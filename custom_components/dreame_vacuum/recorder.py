"""Integration platform for recorder."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, callback

from .dreame import DreameVacuumProperty
from .dreame.const import (
    ATTR_ROOMS,
    ATTR_CURRENT_SEGMENT,
    ATTR_SELECTED_MAP,
    ATTR_DID,
    ATTR_STATUS,
    ATTR_CLEANING_MODE,
    ATTR_SUCTION_LEVEL,
    ATTR_WATER_TANK,
    ATTR_CLEANING_TIME,
    ATTR_CLEANED_AREA,
    ATTR_MOP_PAD_HUMIDITY,
    ATTR_SELF_CLEAN_AREA,
    ATTR_SELF_CLEAN_TIME,
    ATTR_MOP_PAD,  
    ATTR_CALIBRATION,
    ATTR_CLEANING_HISTORY_PICTURE,
    ATTR_CRUISING_HISTORY_PICTURE,
    ATTR_OBSTACLE_PICTURE,
    ATTR_RECOVERY_MAP_PICTURE,
    ATTR_RECOVERY_MAP_FILE,
    ATTR_WIFI_MAP_PICTURE,
)

from .dreame.types import (
    ATTR_ROBOT_POSITION,
    ATTR_ROOM_ICON,
    ATTR_ROTATION,
    ATTR_UPDATED,
    ATTR_FRAME_ID,
)

CAMERA_UNRECORDED_ATTRIBUTES = {
    "access_token",
    "entity_picture",
    ATTR_ROOMS,
    ATTR_CALIBRATION,
    ATTR_CLEANING_HISTORY_PICTURE,
    ATTR_CRUISING_HISTORY_PICTURE,
    ATTR_OBSTACLE_PICTURE,
    ATTR_RECOVERY_MAP_PICTURE,
    ATTR_RECOVERY_MAP_FILE,
    ATTR_WIFI_MAP_PICTURE,
    ATTR_ROBOT_POSITION,
    ATTR_ROOM_ICON,
    ATTR_ROTATION,
    ATTR_UPDATED,
    ATTR_FRAME_ID,
}

VACUUM_UNRECORDED_ATTRIBUTES = {
    ATTR_CURRENT_SEGMENT,
    ATTR_SELECTED_MAP,
    ATTR_DID,
    ATTR_STATUS,
    ATTR_CLEANING_MODE,
    ATTR_SUCTION_LEVEL,
    ATTR_WATER_TANK,
    ATTR_CLEANING_TIME,
    ATTR_CLEANED_AREA,
    ATTR_MOP_PAD_HUMIDITY,
    ATTR_SELF_CLEAN_AREA,
    ATTR_SELF_CLEAN_TIME,
    ATTR_MOP_PAD,
    "fan_speed_list",
    "fan_speed",
    "battery_level",
    "battery_icon",
    "mop_pad_humidity_list",
    "cleaning_mode_list",
    "water_volume_list",
    DreameVacuumProperty.STATUS.name.lower(),
    DreameVacuumProperty.WATER_VOLUME.name.lower(),
    DreameVacuumProperty.CLEANING_MODE.name.lower(),
    DreameVacuumProperty.TIGHT_MOPPING.name.lower(),
    DreameVacuumProperty.ERROR.name.lower(),
    DreameVacuumProperty.CLEANING_TIME.name.lower(),
    DreameVacuumProperty.CLEANED_AREA.name.lower(),
    DreameVacuumProperty.MAIN_BRUSH_TIME_LEFT.name.lower(),
    DreameVacuumProperty.MAIN_BRUSH_LEFT.name.lower(),
    DreameVacuumProperty.SIDE_BRUSH_TIME_LEFT.name.lower(),
    DreameVacuumProperty.SIDE_BRUSH_LEFT.name.lower(),
    DreameVacuumProperty.FILTER_LEFT.name.lower(),
    DreameVacuumProperty.FILTER_TIME_LEFT.name.lower(),
    DreameVacuumProperty.SENSOR_DIRTY_LEFT.name.lower(),
    DreameVacuumProperty.SENSOR_DIRTY_TIME_LEFT.name.lower(),
    DreameVacuumProperty.SECONDARY_FILTER_LEFT.name.lower(),
    DreameVacuumProperty.SECONDARY_FILTER_TIME_LEFT.name.lower(),
    DreameVacuumProperty.MOP_PAD_LEFT.name.lower(),
    DreameVacuumProperty.MOP_PAD_TIME_LEFT.name.lower(),
    DreameVacuumProperty.SILVER_ION_LEFT.name.lower(),
    DreameVacuumProperty.SILVER_ION_TIME_LEFT.name.lower(),
    DreameVacuumProperty.DETERGENT_LEFT.name.lower(),
    DreameVacuumProperty.DETERGENT_TIME_LEFT.name.lower(),
    DreameVacuumProperty.SQUEEGEE_LEFT.name.lower(),
    DreameVacuumProperty.SQUEEGEE_TIME_LEFT.name.lower(),
    DreameVacuumProperty.ONBOARD_DIRTY_WATER_TANK_LEFT.name.lower(),
    DreameVacuumProperty.ONBOARD_DIRTY_WATER_TANK_TIME_LEFT.name.lower(),
    DreameVacuumProperty.DIRTY_WATER_TANK_LEFT.name.lower(),
    DreameVacuumProperty.DIRTY_WATER_TANK_TIME_LEFT.name.lower(),
    DreameVacuumProperty.TOTAL_CLEANED_AREA.name.lower(),
    DreameVacuumProperty.TOTAL_CLEANING_TIME.name.lower(),
    DreameVacuumProperty.CLEANING_COUNT.name.lower(),
    DreameVacuumProperty.CUSTOMIZED_CLEANING.name.lower(),
    DreameVacuumProperty.SERIAL_NUMBER.name.lower(),
    DreameVacuumProperty.NATION_MATCHED.name.lower(),
    DreameVacuumProperty.TOTAL_RUNTIME.name.lower(),
    DreameVacuumProperty.TOTAL_CRUISE_TIME.name.lower(),
}


@callback
def exclude_attributes(hass: HomeAssistant) -> set[str]:
    """Exclude vacuum, camera and sensor attributes from being recorded in the database."""
    return frozenset(CAMERA_UNRECORDED_ATTRIBUTES) | frozenset(VACUUM_UNRECORDED_ATTRIBUTES)
