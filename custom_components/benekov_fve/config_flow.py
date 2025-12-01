"""Full config flow implementation for Benekov FVE Monitor."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_URL, CONF_USERNAME, CONF_PASSWORD

from .const import DOMAIN
import logging
_LOGGER = logging.getLogger(__name__)

# --- Data Schema for the Configuration Form ---
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, description={"suggested_value": "http://your.monitor.api/data"}): cv.url,
        vol.Required(CONF_USERNAME, description={"suggested_value": "Client ID (c_monitor)"}): cv.string,
        vol.Required(CONF_PASSWORD, description={"suggested_value": "Token (t_monitor)"}): cv.string,
        vol.Optional("scan_interval", default=5): cv.positive_int,
    }
)


@config_entries.HANDLERS.register(DOMAIN)
class BenekovFVEConfigFlow(config_entries.ConfigFlow):
    """Handle a config flow for the Benekov FVE Monitor integration.

    This implementation performs a connectivity test by calling the API
    inside Home Assistant's executor and returns helpful form errors.
    """

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            url = user_input[CONF_URL]
            c_monitor = user_input[CONF_USERNAME]
            t_monitor = user_input[CONF_PASSWORD]
            scan_interval_s = user_input.get("scan_interval", 5)

            # Import API lazily to avoid import-time failures
            from .sensor import BenekovFVEAPI

            api = BenekovFVEAPI(self.hass, url, c_monitor, t_monitor)
            
            # Test connectivity before saving
            try:
                # Use hass.async_add_executor_job for blocking I/O (like standard HTTP requests)
                info = await self.hass.async_add_executor_job(api.get_data)
                
                # Check for an explicit API error response
                if isinstance(info, dict) and 'error' in info:
                    # Specific check for the API returning a JSON decode failure message
                    if info['error'] == "JSON_DECODE_FAILED":
                         errors["base"] = "invalid_auth" # Treat as an authentication/data error
                    else:
                         # Handle other specific API errors if known
                         errors["base"] = "cannot_connect"
                         _LOGGER.error("API returned error: %s", info['error'])
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
            except Exception as e:
                _LOGGER.exception("Failed to connect or retrieve data from Benekov FVE Monitor")
                errors["base"] = "cannot_connect" # Network or general HTTP error
        
        # Show form if no input or errors occurred
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

