"""Binary sensor platform for AirPort Express integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AirPlayCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AirPlayBinarySensor(data["airplay"], entry, data["device_info"]),
    ])


class AirPlayBinarySensor(CoordinatorEntity[AirPlayCoordinator], BinarySensorEntity):
    """Binary sensor for AirPlay active session."""

    _attr_has_entity_name = True
    _attr_name = "AirPlay"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: AirPlayCoordinator,
        entry: ConfigEntry,
        device_info: dict,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_airplay_active"
        self._device_info = device_info

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info

    @property
    def is_on(self) -> bool | None:
        """Return true if AirPlay session is active."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.playing
