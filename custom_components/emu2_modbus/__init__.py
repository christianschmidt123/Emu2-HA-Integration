"""EMU2 Modbus custom integration."""

from __future__ import annotations

from typing import Any

from pymodbus.client import ModbusTcpClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import HomeAssistant

from .const import CONF_SLAVE, DOMAIN, PLATFORMS


type Emu2ConfigEntry = ConfigEntry[dict[str, Any]]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the EMU2 Modbus integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: Emu2ConfigEntry) -> bool:
    """Set up EMU2 Modbus from a config entry."""
    client = ModbusTcpClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        timeout=entry.data[CONF_TIMEOUT],
    )
    entry.runtime_data = {
        CONF_HOST: entry.data[CONF_HOST],
        CONF_PORT: entry.data[CONF_PORT],
        CONF_TIMEOUT: entry.data[CONF_TIMEOUT],
        CONF_SLAVE: entry.data[CONF_SLAVE],
        "client": client,
    }
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Emu2ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data["client"].close()
    return unload_ok
