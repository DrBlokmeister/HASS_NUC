"""Youfone integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_COUNTRY, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import STORAGE_DIR, Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from requests.exceptions import ConnectionError

from .client import YoufoneClient
from .const import COORDINATOR_UPDATE_INTERVAL, DOMAIN, PLATFORMS
from .exceptions import (
    BadCredentialsException,
    YoufoneException,
    YoufoneServiceException,
)
from .models import YoufoneItem

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Youfone from a config entry."""
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {}

    for platform in PLATFORMS:
        hass.data[DOMAIN][entry.entry_id].setdefault(platform, set())

    client = YoufoneClient(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        country=entry.data[CONF_COUNTRY],
    )

    storage_dir = Path(f"{hass.config.path(STORAGE_DIR)}/{DOMAIN}")
    if storage_dir.is_file():
        storage_dir.unlink()
    storage_dir.mkdir(exist_ok=True)
    store: Store = Store(hass, 1, f"{DOMAIN}/{entry.entry_id}")
    dev_reg = dr.async_get(hass)
    hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ] = coordinator = YoufoneDataUpdateCoordinator(
        hass,
        config_entry_id=entry.entry_id,
        dev_reg=dev_reg,
        client=client,
        store=store,
    )

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class YoufoneDataUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for Youfone."""

    data: list[YoufoneItem]
    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        dev_reg: dr.DeviceRegistry,
        client: YoufoneClient,
        store: Store,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=COORDINATOR_UPDATE_INTERVAL,
        )
        self._debug = _LOGGER.isEnabledFor(logging.DEBUG)
        self._config_entry_id = config_entry_id
        self._device_registry = dev_reg
        self.store = store
        self.client = client
        self.hass = hass

    async def async_config_entry_first_refresh(self) -> None:
        """Refresh data for the first time when a config entry is setup."""
        self.data = await self.store.async_load() or {}
        await super().async_config_entry_first_refresh()

    async def get_data(self) -> dict | None:
        """Get the data from the Youfone client."""
        self.data = await self.hass.async_add_executor_job(self.client.fetch_data)
        await self.store.async_save(self.data)

    async def _async_update_data(self) -> dict | None:
        """Update data."""
        if self._debug:
            await self.get_data()
        else:
            try:
                await self.get_data()
            except ConnectionError as exception:
                _LOGGER.warning(f"ConnectionError {exception}")
            except YoufoneServiceException as exception:
                _LOGGER.warning(f"YoufoneServiceException {exception}")
            except BadCredentialsException as exception:
                _LOGGER.warning(f"Login failed: {exception}")
            except YoufoneException as exception:
                _LOGGER.warning(f"YoufoneException {exception}")
            except Exception as exception:
                _LOGGER.warning(f"Exception {exception}")

        if len(self.data):
            # Map data item as YoufoneItem if it is restored from the data store
            new_data = {}
            for key, value in self.data.items():
                if not isinstance(value, YoufoneItem):
                    new_data[key] = YoufoneItem(**value)
                else:
                    new_data[key] = value
            self.data = new_data

            current_items = {
                list(device.identifiers)[0][1]
                for device in dr.async_entries_for_config_entry(
                    self._device_registry, self._config_entry_id
                )
            }
            fetched_items = set()
            for item_value in self.data.values():
                device_key = item_value.device_key
                if device_key:
                    fetched_items.add(device_key)

            if stale_items := current_items - fetched_items:
                for device_key in stale_items:
                    if device := self._device_registry.async_get_device(
                        {(DOMAIN, device_key)}
                    ):
                        _LOGGER.debug(
                            f"[init|YoufoneDataUpdateCoordinator|_async_update_data|async_remove_device] {device_key}",
                            True,
                        )
                        self._device_registry.async_remove_device(device.id)
            """
            if fetched_items - current_items:
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(self._config_entry_id)
                )
                return None
            _LOGGER.debug("Returning fetched data")
            """
            return self.data
        return {}