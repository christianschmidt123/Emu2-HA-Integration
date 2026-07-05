"""Sensor platform for reading EMU2 values via Modbus TCP."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
import logging
import struct
from typing import Any

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DATA_TYPE,
    CONF_DEVICE_CLASS,
    CONF_INPUT_TYPE,
    CONF_PRECISION,
    CONF_SCALE,
    CONF_SLAVE,
    CONF_STATE_CLASS,
    CONF_SWAP,
    DEFAULT_SCALE,
    DEFAULT_SENSORS,
    DEFAULT_SWAP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
REGISTER_COUNTS = {
    "float32": 2,
    "uint64": 4,
}


type Emu2ConfigEntry = ConfigEntry[dict[str, Any]]


@dataclass(slots=True)
class SensorDefinition:
    """Definition for one configured sensor."""

    key: str
    name: str
    address: int
    input_type: str
    data_type: str
    swap: str
    slave: int
    scan_interval: int
    unit_of_measurement: str | None
    device_class: str | None
    state_class: str | None
    scale: float
    precision: int | None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Emu2ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EMU2 Modbus sensors from a config entry."""
    runtime_data = entry.runtime_data
    client: ModbusTcpClient = runtime_data["client"]

    @callback
    def _close_client(_: Event) -> None:
        client.close()

    hass.bus.async_listen_once("homeassistant_stop", _close_client)

    lock = asyncio.Lock()
    device_name = entry.data[CONF_NAME]
    device_identifier = f"{entry.data[CONF_HOST]}:{entry.data[CONF_PORT]}"
    slave = entry.data[CONF_SLAVE]

    sensors = [
        Emu2ModbusSensor(
            hass=hass,
            client=client,
            definition=SensorDefinition(
                key=str(sensor["key"]),
                name=str(sensor["name"]),
                address=int(sensor["address"]),
                input_type=str(sensor[CONF_INPUT_TYPE]),
                data_type=str(sensor[CONF_DATA_TYPE]),
                swap=str(sensor.get(CONF_SWAP, DEFAULT_SWAP)),
                slave=slave,
                scan_interval=int(sensor["scan_interval"]),
                unit_of_measurement=_normalize_optional(sensor.get("unit_of_measurement")),
                device_class=_normalize_optional(sensor.get(CONF_DEVICE_CLASS)),
                state_class=_normalize_optional(sensor.get(CONF_STATE_CLASS)),
                scale=float(sensor.get(CONF_SCALE, DEFAULT_SCALE)),
                precision=_normalize_precision(sensor.get(CONF_PRECISION)),
            ),
            lock=lock,
            device_name=device_name,
            device_identifier=device_identifier,
        )
        for sensor in DEFAULT_SENSORS
    ]

    async_add_entities(sensors)


def _normalize_optional(value: object | None) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _normalize_precision(value: object | None) -> int | None:
    if value is None:
        return None
    return int(value)


class Emu2ModbusSensor(SensorEntity):
    """A sensor backed by Modbus TCP registers."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        client: ModbusTcpClient,
        definition: SensorDefinition,
        lock: asyncio.Lock,
        device_name: str,
        device_identifier: str,
    ) -> None:
        """Initialize sensor."""
        self.hass = hass
        self._client = client
        self._def = definition
        self._lock = lock
        self._remove_interval_listener: Callable[[], None] | None = None
        self._device_identifier = device_identifier

        self._attr_name = definition.name
        self._attr_unique_id = f"{device_identifier}_{definition.key}"
        self._attr_native_unit_of_measurement = definition.unit_of_measurement
        self._attr_device_class = definition.device_class
        self._attr_state_class = definition.state_class
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_identifier)},
            name=device_name,
            manufacturer="EMU",
            model="Professional II",
        )

    async def async_added_to_hass(self) -> None:
        """Register update timer."""
        self._remove_interval_listener = async_track_time_interval(
            self.hass,
            self._handle_interval,
            timedelta(seconds=self._def.scan_interval),
        )
        await self._async_refresh()

    async def async_will_remove_from_hass(self) -> None:
        """Remove update timer."""
        if self._remove_interval_listener:
            self._remove_interval_listener()
            self._remove_interval_listener = None

    @callback
    def _handle_interval(self, _: Any) -> None:
        """Refresh state on interval."""
        self.hass.async_create_task(self._async_refresh())

    async def _async_refresh(self) -> None:
        """Fetch and update sensor state."""
        async with self._lock:
            try:
                value = await self.hass.async_add_executor_job(
                    self._read_sensor_value,
                )
            except (ConnectionError, ModbusException, OSError, ValueError) as err:
                _LOGGER.warning(
                    "Failed to update %s (%s): %s",
                    self.entity_id,
                    type(err).__name__,
                    err,
                )
                self._attr_available = False
                self.async_write_ha_state()
                return

        self._attr_native_value = value
        self._attr_available = True
        self.async_write_ha_state()

    def _read_sensor_value(self) -> float:
        """Read and decode one sensor value from Modbus."""
        if not self._client.is_socket_open() and not self._client.connect():
            raise ConnectionError(
                f"Modbus TCP connection failed for {self._device_identifier}"
            )

        try:
            register_count = REGISTER_COUNTS[self._def.data_type]
        except KeyError as err:
            raise ValueError(f"Unsupported data type: {self._def.data_type}") from err
        if self._def.input_type == "holding":
            result = self._client.read_holding_registers(
                address=self._def.address,
                count=register_count,
                slave=self._def.slave,
            )
        else:
            result = self._client.read_input_registers(
                address=self._def.address,
                count=register_count,
                slave=self._def.slave,
            )

        if not hasattr(result, "registers"):
            raise ValueError(
                f"Modbus read failed at address={self._def.address}, slave={self._def.slave}, input_type={self._def.input_type}: {result}"
            )

        registers = list(result.registers)
        if self._def.swap == "word":
            registers.reverse()

        payload = b"".join(struct.pack(">H", register) for register in registers)

        if self._def.data_type == "float32":
            raw_value = struct.unpack(">f", payload)[0]
        else:
            raw_value = float(struct.unpack(">Q", payload)[0])

        scaled = raw_value * self._def.scale
        if self._def.precision is not None:
            return round(scaled, self._def.precision)

        return scaled
