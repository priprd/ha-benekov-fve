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

    return {
        "Diaggnostics fetched successfully": "Yes",
    }
