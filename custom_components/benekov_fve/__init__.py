"""The Benekov FVE Monitor integration."""
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
DOMAIN = "benekov_fve"
# Tato funkce je volána, když je integrace spuštěna z konfiguračního toku.
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Benekov FVE Monitor from a config entry."""
    # V této fázi obvykle uložíte data z config_entry do 'data' a načtete platformy (např. 'sensor').
    
    # Uložení dat pro pozdější použití (např. v sensor.py)
    hass.data.setdefault("benekov_fve", {})
    hass.data["benekov_fve"][entry.entry_id] = entry.data

    # Načtení platformy 'sensor'.
    await hass.config_entries.async_forward_entry_setup(entry, "sensor")
    
    return True

# Tato funkce je volána, když je integrace odebrána.
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Odstranění platformy 'sensor'.
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    
    if unload_ok:
        # Vyčištění dat
        hass.data["benekov_fve"].pop(entry.entry_id)

    return unload_ok
