from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Unraid Monitor switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for key, value in coordinator.data.items():
        if key.endswith("_container_state") and isinstance(value, bool):
            container_name = key.replace("_container_state", "")
            entities.append(UnraidDockerContainerSwitch(coordinator, container_name))

    async_add_entities(entities)

class UnraidDockerContainerSwitch(SwitchEntity):
    """Representation of a Docker container switch."""

    def __init__(self, coordinator, container_name):
        """Initialize the switch."""
        self.coordinator = coordinator
        self.container_name = container_name
        self._attr_name = f"Docker {container_name}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{container_name}_switch"

    @property
    def is_on(self):
        """Return true if the container is running."""
        state = self.coordinator.data.get(f"{self.container_name}_container_state")
        return state

    async def async_turn_on(self, **kwargs):
        """Start the Docker container."""
        await self.coordinator.start_container(self.container_name)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Stop the Docker container."""
        await self.coordinator.stop_container(self.container_name)
        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self):
        """Disable polling. Coordinator notifies entity of updates."""
        return False

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
