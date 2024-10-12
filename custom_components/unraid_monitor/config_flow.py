import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_KEY,
    CONF_POLL_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_POLL_INTERVAL,
)

class UnraidConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Unraid Monitor."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate the connection here
            from .ssh_connection import SSHConnection
            try:
                connection = SSHConnection(
                    user_input[CONF_HOST],
                    user_input.get(CONF_PORT, DEFAULT_PORT),
                    user_input[CONF_USERNAME],
                    user_input.get(CONF_PASSWORD),
                    user_input.get(CONF_KEY),
                )
                await connection.connect()
                await connection.disconnect()
                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input,
                )
            except Exception as e:
                errors["base"] = "connection_failed"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_USERNAME): str,
                vol.Optional(CONF_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(multiline=True)
                ),
                vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): int,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return UnraidOptionsFlowHandler(config_entry)


class UnraidOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Unraid Monitor options."""

    def __init__(self, config_entry):
        """Initialize Unraid options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the Unraid options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_POLL_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
                    ),
                ): int,
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
