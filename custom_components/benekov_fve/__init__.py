"""The Benekov FVE Monitor integration."""
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryNotReady
from .const import DOMAIN, LOGGER
import logging

_LOGGER = LOGGER or logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Benekov FVE Monitor from a config entry.

    Perform a quick connectivity test before forwarding setup to platforms.
    If the external API is not reachable, raise `ConfigEntryNotReady` so
    Home Assistant will retry setup later, rather than forwarding the
    config entry to platforms which may fail.
    """

    hass.data.setdefault(DOMAIN, {})
    # Store a mutable container per entry (don't store the MappingProxy `entry.data`
    # directly because it's immutable). Keep the original data under the
    # `config` key so other code can read it if needed.
    hass.data[DOMAIN].setdefault(entry.entry_id, {})
    hass.data[DOMAIN][entry.entry_id]["config"] = entry.data

    # Lazy import API to avoid import-time side effects
    try:
        from .sensor import BenekovFVEAPI
    except Exception as err:
        _LOGGER.exception("Failed to import BenekovFVEAPI during setup: %s", err)
        raise ConfigEntryNotReady from err

    url = entry.data.get(CONF_URL)
    c_monitor = entry.data.get(CONF_USERNAME)
    t_monitor = entry.data.get(CONF_PASSWORD)

    api = BenekovFVEAPI(hass, url, c_monitor, t_monitor)

    try:
        info = await hass.async_add_executor_job(api.get_data)
        # Treat explicit API error responses as not ready
        if isinstance(info, dict) and info.get("error"):
            _LOGGER.error("API reported error during initial setup: %s", info.get("error"))
            raise ConfigEntryNotReady("API error during initial setup")
    except ConfigEntryNotReady:
        raise
    except Exception as err:
        _LOGGER.exception("Initial connection to Benekov FVE API failed: %s", err)
        raise ConfigEntryNotReady from err

    # Forward setup to the sensor platform after connectivity verified
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration and register a simple debug service.

    The service `benekov_fve.get_wifi` accepts optional `entry_id` and
    logs the current `wifi_percent` value (from coordinator data if
    available, otherwise performs a one-off API call in the executor).
    This is a lightweight troubleshooting helper and can be removed later.
    """
    from .const import DOMAIN

    async def _handle_get_wifi(call):
        entry_id = call.data.get("entry_id") if call.data else None
        hass.data.setdefault(DOMAIN, {})

        # If no entry_id provided and exactly one entry is configured, use it
        if not entry_id:
            entries = list(hass.data[DOMAIN].keys())
            if len(entries) == 1:
                entry_id = entries[0]

        if not entry_id or entry_id not in hass.data[DOMAIN]:
            _LOGGER.error("benekov_fve.get_wifi: entry_id not provided or unknown")
            return

        entry_container = hass.data[DOMAIN].get(entry_id, {})
        coordinator = entry_container.get("coordinator")
        wifi = None

        if coordinator is not None and getattr(coordinator, "data", None) is not None:
            wifi = coordinator.data.get("wifi_percent")
        else:
            # Try a one-off API call
            try:
                from .sensor import BenekovFVEAPI
                from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD

                cfg = entry_container.get("config") or {}
                api = BenekovFVEAPI(hass, cfg.get(CONF_URL), cfg.get(CONF_USERNAME), cfg.get(CONF_PASSWORD))
                result = await hass.async_add_executor_job(api.get_data)
                if isinstance(result, dict):
                    wifi = result.get("wifi_percent")
            except Exception as err:
                _LOGGER.exception("benekov_fve.get_wifi: API call failed: %s", err)

        _LOGGER.info("benekov_fve.get_wifi: entry_id=%s wifi_percent=%s", entry_id, wifi)
        # Fire an event so users can capture the result programmatically
        hass.bus.async_fire("benekov_fve_wifi", {"entry_id": entry_id, "wifi_percent": wifi})

    hass.services.async_register(DOMAIN, "get_wifi", _handle_get_wifi)

    return True
