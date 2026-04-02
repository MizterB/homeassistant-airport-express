"""Button platform for AirPort Express integration."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .acp import async_reboot
from .const import CONF_HOST, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons from a config entry."""
    device_info = hass.data[DOMAIN][entry.entry_id]["device_info"]
    async_add_entities([RebootButton(entry, device_info)])


class RebootButton(ButtonEntity):
    """Button to reboot the AirPort Express."""

    _attr_has_entity_name = True
    _attr_name = "Reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_icon = "mdi:restart"

    def __init__(self, entry: ConfigEntry, device_info: dict) -> None:
        """Initialize."""
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_reboot"
        self._device_info = device_info

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        host = self._entry.data[CONF_HOST]
        password = self._entry.data.get(CONF_PASSWORD, "")
        _LOGGER.info("Rebooting AirPort Express at %s", host)
        await async_reboot(host, password)
