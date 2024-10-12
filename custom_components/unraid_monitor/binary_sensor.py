from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Unraid Monitor binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for key in coordinator.data:
        if isinstance(coordinator.data[key], bool):
            entities.append(UnraidBinarySensor(coordinator, key))

    async_add_entities(entities)


class UnraidBinarySensor(BinarySensorEntity):
    """Representation of a Unraid binary sensor."""

    def __init__(self, coordinator, key):
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self.key = key
        self._attr_name = f"Unraid {key.replace('_', ' ').title()}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self.coordinator.data.get(self.key)

    @property
    def should_poll(self):
        """Disable polling. Coordinator notifies entity of updates."""
        return False

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
