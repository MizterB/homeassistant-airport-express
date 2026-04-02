"""Config flow for AirPort Express integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .acp import ACPError, async_validate_connection
from .const import CONF_HOST, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PASSWORD, default=""): str,
    }
)


class AirPortExpressConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AirPort Express."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._discovered_host: str | None = None
        self._discovered_name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            password = user_input.get(CONF_PASSWORD, "")

            try:
                device_name = await async_validate_connection(host, password)
            except ACPError:
                errors["base"] = "cannot_connect"
            except OSError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=device_name,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: dict
    ) -> FlowResult:
        """Handle zeroconf discovery of an AirPort Express."""
        host = str(discovery_info.ip_address if hasattr(discovery_info, "ip_address") else discovery_info.get("host", ""))
        name_raw = discovery_info.name if hasattr(discovery_info, "name") else discovery_info.get("name", "AirPort Express")
        name = name_raw.removesuffix("._airport._tcp.local.")

        # Use host as unique ID to prevent duplicate discoveries
        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured()

        self._discovered_host = host
        self._discovered_name = name
        self.context["title_placeholders"] = {"name": name}

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user confirmation of a discovered device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            password = user_input.get(CONF_PASSWORD, "")

            try:
                device_name = await async_validate_connection(
                    self._discovered_host, password
                )
            except ACPError:
                errors["base"] = "cannot_connect"
            except OSError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=device_name,
                    data={
                        CONF_HOST: self._discovered_host,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {vol.Optional(CONF_PASSWORD, default=""): str}
            ),
            errors=errors,
            description_placeholders={"name": self._discovered_name},
        )
