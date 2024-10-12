from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfInformation
)
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Unraid Monitor sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for key, value in coordinator.data.items():
        if "_container_state" not in key and not isinstance(value, bool):
            entities.append(UnraidSensor(coordinator, key))

    async_add_entities(entities)


class UnraidSensor(SensorEntity):
    """Representation of a Unraid sensor."""

    def __init__(self, coordinator, key):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.key = key
        self._attr_name = f"Unraid {key.replace('_', ' ').title()}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_class, self._attr_unit_of_measurement, self._attr_icon = self._determine_sensor_attributes()

    def _determine_sensor_attributes(self):
        """Determine the device class, unit, and icon based on the sensor type."""
        device_class = None
        unit = None
        icon = "mdi:chip"  # Default icon for generic sensors

        if "temperature" in self.key:
            device_class = SensorDeviceClass.TEMPERATURE
            unit = UnitOfTemperature.CELSIUS
            icon = "mdi:thermometer"

        elif "cpu_usage" in self.key or "cpu" in self.key:
            # CPU usage should not use 'power' device class; we use percentage
            device_class = None  # No device class
            unit = PERCENTAGE
            icon = "mdi:chip"

        elif "mem_usage" in self.key or "memory" in self.key:
            device_class = SensorDeviceClass.DATA_SIZE
            unit = UnitOfInformation.MEGABYTES
            icon = "mdi:memory"

        elif "disk_space" in self.key:
            device_class = SensorDeviceClass.DATA_SIZE
            unit = UnitOfInformation.MEGABYTES
            icon = "mdi:harddisk"

        elif "link_speed" in self.key:
            unit = "Mb/s"
            icon = "mdi:speedometer"

        return device_class, unit, icon

    @property
    def native_value(self):
        """Return the state of the sensor with any necessary conversions."""
        raw_value = self.coordinator.data.get(self.key)

        if raw_value is None:
            return None  # Indicate that the sensor is unavailable

        # Perform conversions based on sensor type
        if "mem_usage" in self.key or "memory" in self.key:
            return self._convert_memory_to_mib(raw_value)

        if "temperature" in self.key or "cpu_usage" in self.key:
            return float(raw_value)  # Ensure temperatures and CPU usage are floats

        if "link_speed" in self.key:
            # Assuming the raw value is something like "1000Mb/s" - strip "Mb/s"
            return int(raw_value.replace("Mb/s", "").strip())

        return raw_value

    def _convert_memory_to_mib(self, memory_value):
        """Convert a memory string like '6.457MiB' to a float in MiB."""
        memory_value = str(memory_value)  # Ensure memory_value is treated as a string
        if "MiB" in memory_value:
            return float(memory_value.replace("MiB", "").strip())
        elif "GiB" in memory_value:
            return float(memory_value.replace("GiB", "").strip()) * 1024
        elif "KiB" in memory_value:
            return float(memory_value.replace("KiB", "").strip()) / 1024
        elif "TiB" in memory_value:
            return float(memory_value.replace("TiB", "").strip()) * 1024 * 1024
        return float(memory_value)  # Fallback for other types of values

    @property
    def should_poll(self):
        """Disable polling. Coordinator notifies entity of updates."""
        return False

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
