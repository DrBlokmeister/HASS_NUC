"""Unraid sensor integration."""

import asyncio
import logging
import requests
import json

from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    TEMP_CELSIUS,
    DATA_GIGABYTES,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "unraid"
SENSOR_PREFIX = "Unraid "

SENSOR_TYPES = {
    "temp": ["Temperature", TEMP_CELSIUS],
    "used": ["Used Space", DATA_GIGABYTES],
    "free": ["Free Space", DATA_GIGABYTES],
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Unraid platform."""

    host = config["host"]
    port = config["port"]
    password = config["password"]

    url = f"http://{host}:{port}/plugins/dynamix.docker.manager/include/Unraid.php"
    headers = {"Authorization": f"Bearer {password}"}

    entities = []

    for sensor_type in SENSOR_TYPES:
        for share in await hass.async_add_executor_job(get_shares, url, headers):
            entities.append(UnraidSensor(SENSOR_PREFIX + share["name"] + " " + SENSOR_TYPES[sensor_type][0], url, headers, sensor_type, share))

    async_add_entities(entities, True)


def get_shares(url, headers):
    """Get a list of shares from the Unraid server."""

    shares = []

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        _LOGGER.error("Error getting shares from Unraid server: %s", error)
        return shares

    data = json.loads(response.text)

    for share in data["shares"]:
        shares.append(share)

    return shares


class UnraidSensor(Entity):
    """Representation of a sensor."""

    def __init__(self, name, url, headers, sensor_type, share):
        """Initialize the sensor."""

        self._name = name
        self._url = url
        self._headers = headers
        self._sensor_type = sensor_type
        self._state = None
        self._share = share

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return SENSOR_TYPES[self._sensor_type][1]

    async def async_update(self):
        """Get the latest data from the Unraid API."""

        try:
            response = requests.get(self._url, headers=self._headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            _LOGGER.error("Error getting data from Unraid server: %s", error)
            return

        data = json.loads(response.text)

        if self._sensor_type == "temp":
            for sensor in data["sensors"]:
                if sensor["name"] == self._share["name"]:
                    self._state = sensor["temp"]
        elif self._sensor_type == "used":
            self._state = self._share["used"]
        elif self._sensor_type == "free":
            self._state = self._share["free"]
