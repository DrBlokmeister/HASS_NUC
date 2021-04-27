from typing import Callable, List, Optional

from aiotruenas_client import CachingMachine as Machine
from aiotruenas_client.virtualmachine import VirtualMachine, VirtualMachineState
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import slugify

from . import TrueNASBinarySensor, TrueNASVirtualMachineEntity
from .const import (
    DOMAIN,
    SCHEMA_SERVICE_VM_RESTART,
    SCHEMA_SERVICE_VM_START,
    SCHEMA_SERVICE_VM_STOP,
    SERVICE_VM_RESTART,
    SERVICE_VM_START,
    SERVICE_VM_STOP,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict,
    async_add_entities: Callable,
):
    """Set up the TrueNAS switches."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)

    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        SERVICE_VM_START,
        SCHEMA_SERVICE_VM_START,
        "start",
    )
    platform.async_register_entity_service(
        SERVICE_VM_STOP,
        SCHEMA_SERVICE_VM_STOP,
        "stop",
    )
    platform.async_register_entity_service(
        SERVICE_VM_RESTART,
        SCHEMA_SERVICE_VM_RESTART,
        "restart",
    )


def _get_machine(hass: HomeAssistant, entry: dict) -> Machine:
    machine = hass.data[DOMAIN][entry.entry_id]["machine"]
    assert machine is not None
    return machine


def _create_entities(hass: HomeAssistant, entry: dict) -> List[Entity]:
    entities = []

    machine = _get_machine(hass, entry)
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]

    for vm in machine.vms:
        entities.append(
            VirturalMachineIsRunningBinarySensor(entry, name, vm, coordinator)
        )

    return entities


class VirturalMachineIsRunningBinarySensor(
    TrueNASVirtualMachineEntity, TrueNASBinarySensor, BinarySensorEntity
):
    def __init__(
        self,
        entry: dict,
        name: str,
        virtural_machine: VirtualMachine,
        coordinator: DataUpdateCoordinator,
    ) -> None:
        self._vm = virtural_machine
        super().__init__(entry, name, coordinator)

    @property
    def name(self) -> str:
        """Return the name of the virtural machine."""
        return f"{self._vm.name} Virtural Machine Running"

    @property
    def unique_id(self) -> str:
        return slugify(
            f"{self._entry.unique_id}-{self._vm.id}_binary_sensor",
        )

    @property
    def icon(self) -> str:
        """Return an icon for the virtural machine."""
        return "mdi:server"

    def _get_state(self) -> Optional[bool]:
        """Returns the current state of the virtural machine."""
        if self._vm.available:
            return self._vm.status == VirtualMachineState.RUNNING
        return None
