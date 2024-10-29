import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .controller_api import ControllerAPI
from .gateway_api import GatewayAPI
from .coordinator import AlphaInnotecCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alpha Innotec from a config entry."""
    _LOGGER.debug("Setting up Alpha Innotec component")

    try:
        # Initialize Controller API
        controller_api = ControllerAPI(
            entry.data['controller_ip'],
            entry.data['controller_username'],
            entry.data['controller_password']
        )
        controller_api = await hass.async_add_executor_job(controller_api.login)
        _LOGGER.info("Controller API initialized successfully")

        # Initialize Gateway API
        gateway_api = GatewayAPI(
            entry.data['gateway_ip'],
            entry.data['gateway_password']
        )
        gateway_api = await hass.async_add_executor_job(gateway_api.login)
        _LOGGER.info("Gateway API initialized successfully")

        # Store APIs in hass.data
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
            "controller_api": controller_api,
            "gateway_api": gateway_api,
        }

        # Initialize Coordinator with ConfigEntry
        coordinator = AlphaInnotecCoordinator(hass, entry)
        hass.data[DOMAIN][entry.entry_id]['coordinator'] = coordinator

        # Start the coordinator
        await coordinator.async_config_entry_first_refresh()

        # Forward setup to platforms
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        _LOGGER.info("Alpha Innotec component setup complete")
        return True
    except Exception as e:
        _LOGGER.exception("Error setting up Alpha Innotec component: %s", e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Alpha Innotec component")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Alpha Innotec component unloaded successfully")

    return unload_ok
