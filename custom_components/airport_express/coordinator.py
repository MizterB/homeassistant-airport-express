"""Data update coordinators for AirPort Express integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .acp import (
    ACPError,
    AirPlayStatus,
    DeviceProperties,
    async_get_airplay_status,
    async_get_properties,
)
from .const import AIRPLAY_POLL_INTERVAL, PROPERTIES_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AirPlayCoordinator(DataUpdateCoordinator[AirPlayStatus]):
    """Coordinator for fast AirPlay status polling (2s)."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name="AirPort Express AirPlay",
            update_interval=timedelta(seconds=AIRPLAY_POLL_INTERVAL),
        )
        self.host = host

    async def _async_update_data(self) -> AirPlayStatus:
        try:
            session = async_get_clientsession(self.hass)
            return await async_get_airplay_status(self.host, session)
        except ACPError as err:
            raise UpdateFailed(f"AirPlay status query failed: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"AirPlay status query failed: {err}") from err


class PropertiesCoordinator(DataUpdateCoordinator[DeviceProperties]):
    """Coordinator for slow ACP property polling (60s)."""

    def __init__(self, hass: HomeAssistant, host: str, password: str) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name="AirPort Express Properties",
            update_interval=timedelta(seconds=PROPERTIES_POLL_INTERVAL),
        )
        self.host = host
        self.password = password

    async def _async_update_data(self) -> DeviceProperties:
        try:
            return await async_get_properties(self.host, self.password)
        except ACPError as err:
            raise UpdateFailed(f"ACP property query failed: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"ACP property query failed: {err}") from err
