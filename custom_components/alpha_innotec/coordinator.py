import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .controller_api import ControllerAPI
from .gateway_api import GatewayAPI
from .const import DOMAIN, MODULE_TYPE_SENSOR, MODULE_TYPE_SENSE_CONTROL
from .structs.Thermostat import Thermostat
from .structs.Valve import Valve

_LOGGER = logging.getLogger(__name__)


class AlphaInnotecCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Alpha Innotec data fetching."""

    data: dict[str, list[Valve | Thermostat]]
    last_successful_update: datetime | None = None
    grace_period: timedelta = timedelta(minutes=10)

    def __init__(self, hass: HomeAssistant, config_entry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Alpha Innotec",
            update_interval=timedelta(seconds=10),
        )

        self.config_entry = config_entry

        # Initialize APIs from hass.data
        try:
            self.controller_api: ControllerAPI = hass.data[DOMAIN][config_entry.entry_id]['controller_api']
            self.gateway_api: GatewayAPI = hass.data[DOMAIN][config_entry.entry_id]['gateway_api']
        except KeyError as e:
            _LOGGER.error("Initialization error: %s", e)
            raise

    async def _async_update_data(self) -> dict[str, list[Valve | Thermostat]]:
        """Fetch data from APIs and update the coordinator."""
        try:
            _LOGGER.debug("Starting data update from APIs")
            db_modules: dict = await self.hass.async_add_executor_job(self.gateway_api.db_modules)
            all_modules: dict = await self.hass.async_add_executor_job(self.gateway_api.all_modules)
            room_list: dict = await self.hass.async_add_executor_job(self.controller_api.room_list)

            thermostats: list[Thermostat] = []
            valves: list[Valve] = []

            for room_id in all_modules:
                room_module = all_modules.get(room_id, {})
                room = await self.hass.async_add_executor_job(
                    self.controller_api.room_details, room_id, room_list
                )

                if room is None:
                    _LOGGER.warning("Room details not found for room ID: %s", room_id)
                    continue

                current_temperature = None
                battery_percentage = None

                for module_id in room_module.get('modules', []):
                    if module_id not in db_modules.get('modules', {}):
                        _LOGGER.debug("Module ID %s not found in DB modules", module_id)
                        continue

                    module_details = db_modules['modules'][module_id]

                    if module_details.get("type") in [MODULE_TYPE_SENSOR, MODULE_TYPE_SENSE_CONTROL]:
                        current_temperature = module_details.get("currentTemperature", current_temperature)
                        battery_percentage = module_details.get("battery", battery_percentage)

                if room.get('status', 'problem') == 'problem':
                    _LOGGER.info("According to the API there is a problem with: %s", room['name'])

                thermostat = Thermostat(
                    identifier=room_id,
                    name=room['name'],
                    current_temperature=current_temperature,
                    desired_temperature=room.get('desiredTemperature'),
                    minimum_temperature=room.get('minTemperature'),
                    maximum_temperature=room.get('maxTemperature'),
                    cooling=room.get('cooling'),
                    cooling_enabled=room.get('coolingEnabled'),
                    battery_percentage=battery_percentage
                )

                thermostats.append(thermostat)

            for module_id, module in db_modules.get("modules", {}).items():
                if module.get("productId") != 3:
                    continue

                for instance in module.get("instances", []):
                    valve_id = '0' + instance.get('instance', '') + module.get('deviceid', '')[2:]

                    used = False
                    for room_id in all_modules:
                        if valve_id in all_modules[room_id].get("modules", []):
                            used = True
                            break

                    valve = Valve(
                        identifier=valve_id,
                        name=f"{module.get('name', 'Unknown')}-{instance.get('instance', '')}",
                        instance=instance.get("instance"),
                        device_id=module.get("deviceid", ""),
                        device_name=module.get("name", "Unknown"),
                        status=instance.get("status", False),
                        used=used
                    )

                    valves.append(valve)

            self.last_successful_update = datetime.now()
            _LOGGER.debug("Fetched %d thermostats and %d valves", len(thermostats), len(valves))
            return {
                'valves': valves,
                'thermostats': thermostats
            }

        except Exception as e:
            _LOGGER.error("Error during data update: %s", e)
            raise

    @property
    def is_available(self) -> bool:
        """Determine if the sensors should be available based on the grace period."""
        if self.last_successful_update is None:
            # Initially available until a failure occurs
            return True
        return (datetime.now() - self.last_successful_update) < self.grace_period
