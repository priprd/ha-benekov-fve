"""Minimal config flow used for debugging handler loading errors."""

import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_URL

from .const import DOMAIN

# Small schema to exercise the form UI without side effects.
# Use `cv.string` instead of `cv.url` to ensure HA can convert the
# schema to a UI form without raising conversion errors.
DATA_SCHEMA = vol.Schema({vol.Required(CONF_URL): cv.string})


@config_entries.HANDLERS.register(DOMAIN)
class BenekovFVEConfigFlow(config_entries.ConfigFlow):
    """Minimal, safe config flow for testing handler registration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        # Create entry without contacting external services — used only for testing
        return self.async_create_entry(title="Benekov FVE (test)", data=user_input)

