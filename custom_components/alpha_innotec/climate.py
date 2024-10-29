"""Platform for climate integration."""
from __future__ import annotations

import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityDescription,
    ClimateEntityFeature,
    HVACMode
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import UndefinedType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .controller_api import Thermostat
from .coordinator import AlphaInnotecCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities
):
    """Set up the climate platform."""
    _LOGGER.debug("Setting up climate sensors")

    coordinator: AlphaInnotecCoordinator = hass.data[DOMAIN][entry.entry_id]['coordinator']

    await coordinator.async_config_entry_first_refresh()

    entities = [
        AlphaInnotecClimateSensor(
            coordinator=coordinator,
            description=ClimateEntityDescription(""),
            thermostat=thermostat
        )
        for thermostat in coordinator.data.get("thermostats", [])
    ]

    async_add_entities(entities)


class AlphaInnotecClimateSensor(CoordinatorEntity, ClimateEntity):
    """Representation of a Climate Sensor."""

    _attr_precision = 0.1
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.OFF]

    def __init__(
        self,
        coordinator: AlphaInnotecCoordinator,
        description: ClimateEntityDescription,
        thermostat: Thermostat
    ) -> None:
        """Initialize the climate sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.thermostat = thermostat

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (DOMAIN, self.thermostat.identifier)
            },
            name=self.thermostat.name,
            manufacturer=MANUFACTURER,
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for this device."""
        return self.thermostat.identifier

    @property
    def name(self) -> str | UndefinedType | None:
        """Return the name of the sensor."""
        return self.thermostat.name

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.is_available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        for thermostat in self.coordinator.data.get('thermostats', []):
            if thermostat.identifier == self.thermostat.identifier:
                self.thermostat = thermostat
                break

        _LOGGER.debug("Updating climate sensor: %s", self.thermostat.identifier)

        self.async_write_ha_state()

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self.thermostat.current_temperature if isinstance(self.thermostat.current_temperature, (float, int)) else None

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self.thermostat.desired_temperature if isinstance(self.thermostat.desired_temperature, (float, int)) else None

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            try:
                await self.hass.async_add_executor_job(
                    self.coordinator.hass.data[DOMAIN][self.coordinator.config_entry.entry_id]['controller_api'].set_temperature,
                    self.thermostat.identifier,
                    temp
                )
                self.thermostat.desired_temperature = temp
                _LOGGER.debug("Set temperature for %s to %s", self.thermostat.identifier, temp)
            except Exception as e:
                _LOGGER.error("Error setting temperature for %s: %s", self.thermostat.identifier, e)
                self.async_write_ha_state()

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current HVAC mode."""
        return HVACMode.AUTO

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available HVAC modes."""
        return self._attr_hvac_modes
