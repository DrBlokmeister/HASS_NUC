"""Platform for binary sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import UndefinedType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AlphaInnotecCoordinator
from .structs.Valve import Valve

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities
):
    """Set up the binary sensor platform."""
    _LOGGER.debug("Setting up binary sensors")
    
    coordinator: AlphaInnotecCoordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']
    
    await coordinator.async_config_entry_first_refresh()
    
    entities = [
        AlphaHomeBinarySensor(
            coordinator=coordinator,
            description=BinarySensorEntityDescription(""),
            valve=valve
        )
        for valve in coordinator.data.get("valves", [])
    ]
    
    async_add_entities(entities)


class AlphaHomeBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Binary Sensor."""

    def __init__(
        self,
        coordinator: AlphaInnotecCoordinator,
        description: BinarySensorEntityDescription,
        valve: Valve
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.valve = valve

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, self.valve.identifier)
            },
            name=self.valve.name,
            manufacturer=MANUFACTURER,
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for this device."""
        return self.valve.identifier

    @property
    def name(self) -> str | UndefinedType | None:
        """Return the name of the sensor."""
        return self.valve.name

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.is_available

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.valve.status if self.coordinator.is_available else None

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the class of the sensor."""
        return BinarySensorDeviceClass.OPENING

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        for valve in self.coordinator.data.get('valves', []):
            if valve.identifier == self.valve.identifier:
                self.valve = valve
                break

        _LOGGER.debug("Updating binary sensor: %s", self.valve.identifier)

        self.async_write_ha_state()
