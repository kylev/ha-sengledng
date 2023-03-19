"""Light data objects.

These should hide the ugly details and provide something convenient for a
LightEntity to use. I bed this shit does everthing but word wrap.
"""
from __future__ import annotations

import logging
import math
from collections import UserDict  # TODO Aspire to remove.
from typing import Any


from homeassistant.components.light import ColorMode

from .const import (
    PACKET_BRIGHTNESS,
    PACKET_COLOR_MODE,
    PACKET_ONLINE,
    PACKET_RGB_COLOR,
    PACKET_COLOR_TEMP,
    PACKET_SW_VERSION,
    PACKET_VALUE_ON,
    PACKET_SWITCH,
    PACKET_MODEL,
)


_LOGGER = logging.getLogger(__name__)


def create_light(discovery: Any) -> SengledLight:
    """Create the appropriate API light for the discovery packet."""
    if PACKET_RGB_COLOR in discovery:
        return ColorSengledLight(discovery)
    if PACKET_BRIGHTNESS in discovery:
        return SengledLight(discovery)

    _LOGGER.warning("Couldn't build light for packet %s", discovery)


def decode_color_temp(value_pct: str, min_mireds: int, max_mireds: int) -> int:
    """Convert Sengled's brightness percentage to mireds given the light's range."""
    return math.ceil(
        max_mireds - ((int(value_pct) / 100.0) * (max_mireds - min_mireds))
    )


def encode_color_temp(value_mireds: int, min_mireds: int, max_mireds: int) -> str:
    """Convert brightness from HA to Sengled."""
    return str(math.ceil((max_mireds - value_mireds) / (max_mireds - min_mireds) * 100))


class SengledLight(UserDict):
    """A base Sengled light."""

    # Figure out these ranges per light?
    # 1,000,000 divided by 2700 Kelvin = 370 Mireds
    max_mireds: int = 400  # Seems about right for mine?
    min_mireds: int = 400  # 1,000,000 divided by 6500 Kelvin = 154 Mireds
    color_temp: int | None = None
    rgb_color: tuple[int, int, int] | None = None
    color_mode: list[str] | None = None

    @property
    def unique_id(self):
        return self["deviceUuid"]

    @property
    def name(self):
        return self["name"]

    @property
    def available(self) -> bool:
        """Is the light available."""
        return self[PACKET_ONLINE] == PACKET_VALUE_ON

    @property
    def sw_version(self) -> str:
        return self[PACKET_SW_VERSION]

    @property
    def is_on(self) -> bool:
        return self[PACKET_SWITCH] == PACKET_VALUE_ON

    @property
    def brightness(self) -> int | None:
        return math.ceil(int(self[PACKET_BRIGHTNESS]) / 100 * 255)

    @property
    def model(self) -> str:
        return self[PACKET_MODEL]

    @property
    def effect_list(self) -> list[str] | None:
        return []

    @property
    def supported_color_modes(self) -> set[str] | None:
        return self["supportAttributes"].split(",")

    @property
    def mqtt_topics(self) -> list[str]:
        """The topic."""
        # Wish I could do "wifielement/{}/consumptionTime"
        return [
            "wifielement/{}/status".format(self.unique_id),
        ]


class ColorSengledLight(SengledLight):
    min_mireds: int = 154  # 1,000,000 divided by 6500 Kelvin = 154 Mireds

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return tuple(int(rgb) for rgb in self[PACKET_RGB_COLOR].split(":"))

    @property
    def color_temp(self) -> int | None:
        packet_temp = self.get(PACKET_COLOR_TEMP)
        if not packet_temp:
            return None
        return decode_color_temp(
            packet_temp,
            self.min_mireds,
            self.max_mireds,
        )

    @property
    def color_mode(self) -> ColorMode | str | None:
        mode = self.get(PACKET_COLOR_MODE)
        match mode:
            case "1":
                return ColorMode.RGB
            case "2":
                return ColorMode.COLOR_TEMP
            case _:
                return None

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
