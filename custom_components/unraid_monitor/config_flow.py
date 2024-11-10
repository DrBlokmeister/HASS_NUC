# config_flow.py

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    # CONF_POLL_INTERVAL,  # Removed from here
)

from .const import (
    DOMAIN,
    CONF_KEY,
    DEFAULT_HOST,
    DEFAULT_USERNAME,
    DEFAULT_PORT,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
)
from .ssh_connection import SSHConnection  # Ensure this import is correct

_LOGGER = logging.getLogger(__name__)

# Define the data schema outside the class for better readability
DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Optional(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT, multiline=True)
        ),
        vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=3600)
        ),
    }
)


class UnraidConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Unraid Monitor."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL  # Define connection class

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return UnraidOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            _LOGGER.debug("User input received: %s", user_input)
            # Validate the connection here
            try:
                connection = SSHConnection(
                    host=user_input[CONF_HOST],
                    port=user_input.get(CONF_PORT, DEFAULT_PORT),
                    username=user_input[CONF_USERNAME],
                    password=user_input.get(CONF_PASSWORD),
                    key=user_input.get(CONF_KEY),
                )
                await connection.connect()
                await connection.disconnect()
                _LOGGER.info(
                    "SSH connection to %s established successfully.",
                    user_input[CONF_HOST],
                )

                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input,
                )
            except Exception as e:
                _LOGGER.error("Connection failed: %s", e)
                errors["base"] = "connection_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )


class UnraidOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Unraid Monitor options."""

    def __init__(self, config_entry):
        """Initialize Unraid options flow."""
        self.config_entry = config_entry
        _LOGGER.debug("Initializing UnraidOptionsFlowHandler")

    async def async_step_init(self, user_input=None):
        """Manage the Unraid options."""
        if user_input is not None:
            _LOGGER.debug("Options user input received: %s", user_input)
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_POLL_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )
