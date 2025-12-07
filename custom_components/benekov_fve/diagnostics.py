from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.diagnostics import async_redact_data

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    This will be displayed in the Home Assistant UI's integration diagnostics
    and included in support bundles. Keep this data minimal and avoid
    exposing secrets.
    """
    _LOGGER.debug("async_get_config_entry_diagnostics called for entry=%s", entry.entry_id)

    # Try to read existing coordinator data (already-polled values)
    entry_container = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = entry_container.get("coordinator")

    wifi_percent = None
    last_update = None

    if coordinator is not None and getattr(coordinator, "data", None) is not None:
        # Use the last polled coordinator data where available
        data = coordinator.data
        wifi_percent = data.get("wifi_percent")
        last_update = data.get("last_update")
    else:
        # Fallback: perform a fresh, short-lived API call using the integration's API
        try:
            # Import locally to avoid import-time side effects
            from .sensor import BenekovFVEAPI
            from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD

            api = BenekovFVEAPI(hass, entry.data[CONF_URL], entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
            # Run blocking call in executor
            result = await hass.async_add_executor_job(api.get_data)
            if isinstance(result, dict):
                wifi_percent = result.get("wifi_percent")
                last_update = result.get("last_update")
        except Exception as err:  # noqa: BLE001 - broad except for diagnostics only
            _LOGGER.exception("Failed to fetch diagnostics data: %s", err)

    return {
        "wifi_percent": wifi_percent,
        "last_update": last_update,
    }
