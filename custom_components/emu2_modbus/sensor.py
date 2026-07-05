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
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import (
    CONF_ADDRESS,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    CONF_TIMEOUT,
    CONF_UNIQUE_ID,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_DATA_TYPE = "data_type"
CONF_DEVICE_CLASS = "device_class"
CONF_INPUT_TYPE = "input_type"
CONF_PRECISION = "precision"
CONF_SCALE = "scale"
CONF_SLAVE = "slave"
CONF_STATE_CLASS = "state_class"
CONF_SWAP = "swap"

INPUT_TYPES = {"holding", "input"}
DATA_TYPES = {"float32", "uint64"}
SWAP_TYPES = {"none", "word"}

SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Required(CONF_ADDRESS): cv.positive_int,
        vol.Optional(CONF_INPUT_TYPE, default="holding"): vol.In(INPUT_TYPES),
        vol.Optional(CONF_DATA_TYPE, default="float32"): vol.In(DATA_TYPES),
        vol.Optional(CONF_SWAP, default="none"): vol.In(SWAP_TYPES),
        vol.Optional(CONF_SLAVE): cv.positive_int,
        vol.Optional(CONF_SCAN_INTERVAL, default=30): cv.positive_int,
        vol.Optional("unit_of_measurement"): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): cv.string,
        vol.Optional(CONF_STATE_CLASS): cv.string,
        vol.Optional(CONF_SCALE, default=1.0): vol.Coerce(float),
        vol.Optional(CONF_PRECISION): cv.positive_int,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME, default="emu_professional_ii"): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=502): cv.port,
        vol.Optional(CONF_TIMEOUT, default=5): vol.Coerce(float),
        vol.Optional(CONF_SLAVE, default=1): cv.positive_int,
        vol.Required(CONF_SENSORS): vol.All(cv.ensure_list, [SENSOR_SCHEMA]),
    }
)


@dataclass(slots=True)
class SensorDefinition:
    """Definition for one configured sensor."""

    name: str
    unique_id: str | None
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


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: Callable[[list[SensorEntity], bool], None],
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up EMU2 Modbus sensors from YAML."""
    client = ModbusTcpClient(
        host=config[CONF_HOST],
        port=config[CONF_PORT],
        timeout=config[CONF_TIMEOUT],
    )

    if not await hass.async_add_executor_job(client.connect):
        _LOGGER.warning(
            "Initial connection to %s:%s failed; retrying during updates",
            config[CONF_HOST],
            config[CONF_PORT],
        )

    @callback
    def _close_client(_: Event) -> None:
        client.close()

    hass.bus.async_listen_once("homeassistant_stop", _close_client)

    lock = asyncio.Lock()
    device_name = config[CONF_NAME]
    device_identifier = f"{config[CONF_HOST]}:{config[CONF_PORT]}"

    sensors: list[Emu2ModbusSensor] = []
    for entry in config[CONF_SENSORS]:
        definition = SensorDefinition(
            name=entry[CONF_NAME],
            unique_id=entry.get(CONF_UNIQUE_ID),
            address=entry[CONF_ADDRESS],
            input_type=entry[CONF_INPUT_TYPE],
            data_type=entry[CONF_DATA_TYPE],
            swap=entry[CONF_SWAP],
            slave=entry.get(CONF_SLAVE, config[CONF_SLAVE]),
            scan_interval=entry[CONF_SCAN_INTERVAL],
            unit_of_measurement=entry.get("unit_of_measurement"),
            device_class=entry.get(CONF_DEVICE_CLASS),
            state_class=entry.get(CONF_STATE_CLASS),
            scale=entry[CONF_SCALE],
            precision=entry.get(CONF_PRECISION),
        )
        sensors.append(
            Emu2ModbusSensor(
                hass=hass,
                client=client,
                definition=definition,
                lock=lock,
                device_name=device_name,
                device_identifier=device_identifier,
            )
        )

    async_add_entities(sensors)


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
        self._attr_unique_id = definition.unique_id
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
            except (ConnectionError, ModbusException, OSError, ValueError, struct.error) as err:
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
        if not getattr(self._client, "connected", False):
            if not self._client.connect():
                raise ConnectionError(
                    f"Modbus TCP connection failed for {self._device_identifier}"
                )

        register_count = 2 if self._def.data_type == "float32" else 4
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

        if result.isError():
            raise ValueError(
                f"Modbus read error at address={self._def.address}, slave={self._def.slave}, input_type={self._def.input_type}: {result}"
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
