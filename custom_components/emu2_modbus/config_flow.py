"""Config flow for the EMU2 Modbus integration."""

from __future__ import annotations

from typing import Any

from pymodbus.client import ModbusTcpClient
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import HomeAssistant

from .const import DEFAULT_NAME, DEFAULT_PORT, DEFAULT_SLAVE, DEFAULT_TIMEOUT, DOMAIN, CONF_SLAVE


def _schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    user_input = user_input or {}
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "192.168.0.76")): str,
            vol.Required(CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_PORT)): int,
            vol.Required(CONF_TIMEOUT, default=user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): vol.Coerce(float),
            vol.Required(CONF_SLAVE, default=user_input.get(CONF_SLAVE, DEFAULT_SLAVE)): int,
        }
    )


async def _can_connect(hass: HomeAssistant, data: dict[str, Any]) -> bool:
    def _try_connect() -> bool:
        client = ModbusTcpClient(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            timeout=data[CONF_TIMEOUT],
        )
        try:
            return client.connect()
        finally:
            client.close()

    return await hass.async_add_executor_job(_try_connect)


class Emu2ModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EMU2 Modbus."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}:{user_input[CONF_SLAVE]}"
            )
            self._abort_if_unique_id_configured()

            if await _can_connect(self.hass, user_input):
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

            errors["base"] = "cannot_connect"

        return self.async_show_form(step_id="user", data_schema=_schema(user_input), errors=errors)
