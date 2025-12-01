"""The Benekov FVE Monitor integration."""
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, LOGGER

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Benekov FVE Monitor from a config entry."""

    hass.data.setdefault("benekov_fve", {})
    hass.data["benekov_fve"][entry.entry_id] = entry.data

    
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    
    if unload_ok:
        hass.data["benekov_fve"].pop(entry.entry_id)

    return unload_ok
