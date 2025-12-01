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
    """Full implementation backup of the config flow.

    This file is a backup of the full config flow implementation and is not
    used by default. It contains the real connectivity checks and lazy
    imports used by the integration. If you want to restore the full
    implementation, rename this file back to `config_flow.py`.
    """

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step (full implementation).

        This function was moved here as a backup. See the minimal
        `config_flow.py` used for debugging.
        """
        errors = {}

        if user_input is not None:
            url = user_input[CONF_URL]
            c_monitor = user_input[CONF_USERNAME]
            t_monitor = user_input[CONF_PASSWORD]
            scan_interval_s = user_input.get("scan_interval", 5)

            from .sensor import BenekovFVEAPI

            api = BenekovFVEAPI(self.hass, url, c_monitor, t_monitor)

            try:
                info = await self.hass.async_add_executor_job(api.get_data)
                if isinstance(info, dict) and "error" in info:
                    if info["error"] == "JSON_DECODE_FAILED":
                        errors["base"] = "invalid_auth"
                    else:
                        errors["base"] = "cannot_connect"
                        _LOGGER.error("API returned error: %s", info["error"])
                else:
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
                _LOGGER.exception("Failed to connect or retrieve data from Benekov FVE Monitor")
                errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA, errors=errors)
