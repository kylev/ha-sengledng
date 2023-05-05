"""Implementations for the Elements series."""
from __future__ import annotations

import math
import logging
import time
from typing import Any, Final


from .api import API
from .api_bulb import APIBulb

PACKET_BRIGHTNESS: Final = "brightness"
PACKET_COLOR_MODE: Final = "colorMode"
PACKET_COLOR_TEMP: Final = "colorTemperature"
PACKET_EFFECT: Final = "effectStatus"
PACKET_MODEL: Final = "typeCode"
PACKET_ONLINE: Final = "online"
PACKET_RGB_COLOR: Final = "color"
PACKET_SW_VERSION: Final = "version"
PACKET_SWITCH: Final = "switch"
PACKET_VALUE_OFF: Final = "0"
PACKET_VALUE_ON: Final = "1"

HA_COLOR_MODE_BRIGHTNESS = "brightness"
HA_COLOR_MODE_COLOR_TEMP = "color_temp"
HA_COLOR_MODE_RGB = "rgb"

_LOGGER = logging.getLogger(__name__)


def _hassify_discovery(packet: dict[str, Any]) -> dict[str, str]:
    result = {}
    for key, value in packet.items():
        if key in {"attributeList"}:
            continue

        if isinstance(value, (list, tuple, str)):
            result[key] = value
        else:
            _LOGGER.warning("Weird value while hass-ifying: %s", (key, value))

    for item in packet["attributeList"]:
        result[item["name"]] = item["value"]

    return result


def _decode_color_temp(value_pct: str, min_mireds: int, max_mireds: int) -> int:
    """Convert Sengled's brightness percentage to mireds given the light's range."""
    return math.ceil(
        max_mireds - ((int(value_pct) / 100.0) * (max_mireds - min_mireds))
    )


def _encode_color_temp(value_mireds: int, min_mireds: int, max_mireds: int) -> str:
    """Convert brightness from HA to Sengled."""
    return str(math.ceil((max_mireds - value_mireds) / (max_mireds - min_mireds) * 100))


class ElementsBulb(APIBulb):
    """A Wifi Elements bulb."""

    _data: dict[str, str]
    _api: API  # Expected from mixed-in class

    def __init__(self, discovery) -> None:
        _LOGGER.debug("%s init %r", self.__class__.__name__, discovery)
        self._data = _hassify_discovery(discovery)

    @property
    def unique_id(self):
        return self._data["deviceUuid"]

    @property
    def name(self):
        return self._data["name"]

    @property
    def available(self) -> bool:
        """Is the light available."""
        return self._data[PACKET_ONLINE] == PACKET_VALUE_ON

    @property
    def is_on(self) -> bool:
        return self._data[PACKET_SWITCH] == PACKET_VALUE_ON

    @property
    def brightness(self) -> int | None:
        return math.ceil(int(self._data[PACKET_BRIGHTNESS]) / 100 * 255)

    @property
    def color_mode(self) -> str | None:
        return {
            "1": HA_COLOR_MODE_RGB,
            "2": HA_COLOR_MODE_COLOR_TEMP
        }.get(self._data.get(PACKET_COLOR_MODE), HA_COLOR_MODE_BRIGHTNESS)

    @property
    def sw_version(self) -> str:
        return self._data[PACKET_SW_VERSION]

    @property
    def model(self) -> str:
        return self._data[PACKET_MODEL]

    @property
    def mqtt_topics(self) -> list[str]:
        """The topic."""
        # Wish I could do "wifielement/{}/consumptionTime"
        return [
            "wifielement/{}/status".format(self.unique_id),
        ]

    async def set_power(self, to_on=True):
        value = PACKET_VALUE_ON if to_on else PACKET_VALUE_OFF
        await self._async_send_updates({"type": PACKET_SWITCH, "value": value})

    async def set_brightness(self, value):
        await self._async_send_updates(
            {
                "type": PACKET_BRIGHTNESS,
                "value": str(math.ceil(value / 255 * 100)),
            }
        )

    async def _async_send_updates(self, *messages):
        extras = {"dn": self.unique_id, "time": int(time.time() * 1000)}

        await self._api.async_mqtt_publish(
            "wifielement/{}/update".format(self.unique_id),
            [message | extras for message in messages],
        )

    def update_bulb(self, payload):
        packet = {}
        for item in payload:
            if len(item) == 0:
                continue
            packet[item["type"]] = item["value"]
        _LOGGER.debug("Applying update to %s %r", self.name, packet)
        self._data.update(packet)


class ElementsColorBulb(ElementsBulb):
    """A Wifi Elements color bulb."""

    @property
    def color_temp(self) -> int | None:
        packet_temp = self._data.get(PACKET_COLOR_TEMP)
        if not packet_temp:
            return None
        return _decode_color_temp(packet_temp, self.min_mireds, self.max_mireds)

    @property
    def effect_list(self) -> list[str] | None:
        return [
            "christmas",
            "colorCycle",
            "festival",
            "halloween",
            "randomColor",
            "rhythm",
            "none",
        ]

    @property
    def max_mireds(self):
        return 400

    @property
    def min_mireds(self):
        return 154

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return tuple(int(rgb) for rgb in self._data[PACKET_RGB_COLOR].split(":"))

    async def set_color(self, value: tuple[int, int, int]):
        await self._async_send_updates(
            {"type": PACKET_RGB_COLOR, "value": ":".join(str(v) for v in value)}
        )

    async def set_effect(self, effect: str, value: bool):
        await self._async_send_updates(
            {"type": effect, "value": PACKET_VALUE_ON if value else PACKET_VALUE_OFF}
        )

    async def set_temperature(self, temp_mireds):
        await self._async_send_updates(
            {
                "type": PACKET_COLOR_TEMP,
                "value": _encode_color_temp(
                    temp_mireds, self.min_mireds, self.max_mireds
                ),
            }
        )
