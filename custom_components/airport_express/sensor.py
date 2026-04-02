"""Sensor platform for AirPort Express integration."""

from __future__ import annotations

from homeassistant.components.sensor import EntityCategory, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PropertiesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    props_coord = data["properties"]
    device_info = data["device_info"]

    async_add_entities([
        FirmwareSensor(props_coord, entry, device_info),
        UptimeSensor(props_coord, entry, device_info),
        IPAddressSensor(props_coord, entry, device_info),
    ])


class AirPortExpressSensor(CoordinatorEntity[PropertiesCoordinator], SensorEntity):
    """Base class for AirPort Express sensors."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: PropertiesCoordinator,
        entry: ConfigEntry,
        device_info: dict,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._entry = entry
        self._device_info = device_info

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class FirmwareSensor(AirPortExpressSensor):
    """Sensor for firmware version."""

    _attr_name = "Firmware"
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator: PropertiesCoordinator, entry: ConfigEntry, device_info: dict) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, device_info)
        self._attr_unique_id = f"{entry.unique_id}_firmware"

    @property
    def native_value(self) -> str | None:
        """Return firmware version."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.firmware


class UptimeSensor(AirPortExpressSensor):
    """Sensor for device uptime."""

    _attr_name = "Uptime"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: PropertiesCoordinator, entry: ConfigEntry, device_info: dict) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, device_info)
        self._attr_unique_id = f"{entry.unique_id}_uptime"

    @property
    def native_value(self) -> str | None:
        """Return formatted uptime."""
        if self.coordinator.data is None:
            return None
        s = self.coordinator.data.uptime_seconds
        hours, rem = divmod(s, 3600)
        mins, secs = divmod(rem, 60)
        if hours > 0:
            return f"{hours}h {mins}m {secs}s"
        if mins > 0:
            return f"{mins}m {secs}s"
        return f"{secs}s"


class IPAddressSensor(AirPortExpressSensor):
    """Sensor for WAN IP address."""

    _attr_name = "IP Address"
    _attr_icon = "mdi:ip-network"

    def __init__(self, coordinator: PropertiesCoordinator, entry: ConfigEntry, device_info: dict) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, device_info)
        self._attr_unique_id = f"{entry.unique_id}_ip_address"

    @property
    def native_value(self) -> str | None:
        """Return WAN IP address."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.wan_ip
