import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD

# Import the base API class to test connectivity
from .sensor import BenekovFVEAPI, DEFAULT_SCAN_INTERVAL

import logging
_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, description={"suggested_value": "http://your.monitor.api/data"}): cv.url,
        # Using CONF_USERNAME/CONF_PASSWORD for c_monitor/t_monitor storage
        vol.Required(CONF_USERNAME, description={"suggested_value": "Client ID (c_monitor)"}): cv.string,
        vol.Required(CONF_PASSWORD, description={"suggested_value": "Token (t_monitor)"}): cv.string,
        vol.Optional("scan_interval", default=DEFAULT_SCAN_INTERVAL.seconds): cv.positive_int,
    }
)

class BenekovFVEConfigFlow(config_entries.ConfigFlow, domain="benekov_fve"):
    """Handle a config flow for the Benekov FVE Monitor integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            url = user_input[CONF_URL]
            c_monitor = user_input[CONF_USERNAME]
            t_monitor = user_input[CONF_PASSWORD]
            scan_interval_s = user_input["scan_interval"]

            # Renamed API class
            api = BenekovFVEAPI(self.hass, url, c_monitor, t_monitor)
            
            # Test connectivity before saving
            try:
                info = await self.hass.async_add_executor_job(api.get_data)
                if 'error' in info and info['error'] == "JSON_DECODE_FAILED":
                    errors["base"] = "invalid_auth" # API returned gibberish or non-JSON
                else:
                    # Success! Create the config entry
                    return self.async_create_entry(
                        title=f"Benekov FVE ({info.get('user_name', 'System')})",
                        data={
                            CONF_URL: url,
                            CONF_USERNAME: c_monitor,
                            CONF_PASSWORD: t_monitor,
                            "scan_interval": scan_interval_s,
                        },
                    )
            except Exception:
                errors["base"] = "cannot_connect" # Network or HTTP error
        
        # Show form if no input or errors occurred
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )
