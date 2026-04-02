"""The AirPort Express integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .acp import async_get_properties
from .const import CONF_HOST, CONF_PASSWORD, DOMAIN
from .coordinator import AirPlayCoordinator, PropertiesCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AirPort Express from a config entry."""
    host = entry.data[CONF_HOST]
    password = entry.data.get(CONF_PASSWORD, "")

    airplay_coordinator = AirPlayCoordinator(hass, host)
    properties_coordinator = PropertiesCoordinator(hass, host, password)

    # Properties coordinator is required — if ACP fails, setup should fail
    await properties_coordinator.async_config_entry_first_refresh()

    # AirPlay coordinator is best-effort — don't block setup if port 7000 is slow
    try:
        await airplay_coordinator.async_config_entry_first_refresh()
    except Exception:
        _LOGGER.warning("AirPlay status not available yet, will retry on next poll")
        await airplay_coordinator.async_request_refresh()

    # Build device info from initial property fetch
    props = properties_coordinator.data
    device_info = {
        "identifiers": {(DOMAIN, entry.unique_id)},
        "name": props.name or entry.title,
        "manufacturer": "Apple",
        "model": props.model,
        "sw_version": props.firmware,
        "serial_number": props.serial,
    }
    if props.mac:
        device_info["connections"] = {("mac", props.mac)}

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "airplay": airplay_coordinator,
        "properties": properties_coordinator,
        "device_info": device_info,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
