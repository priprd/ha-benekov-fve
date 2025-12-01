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
    hass.data[DOMAIN][entry.entry_id] = entry.data

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
