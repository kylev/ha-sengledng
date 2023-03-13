"""SengledNG light platform."""
from __future__ import annotations

import json
import logging
import math
from typing import Any

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
    filter_supported_color_modes,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import ATTRIBUTION, DOMAIN

_LOGGER = logging.getLogger(__name__)

COLOR_TRANSLATIONS = {
    "brightness": ColorMode.BRIGHTNESS,
    "color": ColorMode.RGB,
    "colorTemperature": ColorMode.COLOR_TEMP,
}
COLOR_SOLO_UPDATES = {"brightness", "color"}


def percent_to_mireds(pct_str: str, max_mireds: int, min_mireds: int) -> int:
    """Convert Sengled's brightness percentage to mireds given the light's range."""
    return int(max_mireds - ((int(pct_str) / 100.0) * (max_mireds - min_mireds)))


class BaseLight(LightEntity):
    """Base Light"""

    _light: DiscoveryInfoType = {}
    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False

    def __init__(self, info: DiscoveryInfoType) -> None:
        _LOGGER.debug("BaseLight init %r", info)
        self._light = info
        self._device_id = info["deviceUuid"]
        self._attr_unique_id = info["deviceUuid"]

        self._attr_device_info = DeviceInfo(
            manufacturer="Sengled", model=info["typeCode"], sw_version=info["version"]
        )

    @property
    def name(self) -> str | None:
        return self._light["name"]

    @property
    def is_on(self) -> bool | None:
        return self._light["switch"] == "1"

    @property
    def available(self) -> bool:
        return self._light["online"] == "1"

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        return filter_supported_color_modes(
            [COLOR_TRANSLATIONS[k] for k in self._light["supportAttributes"].split(",")]
        )

    @property
    def brightness(self) -> int | None:
        return math.ceil(int(self._light["brightness"]) / 100 * 255)

    def _handle_packet(self, packet):
        """Update state"""
        _LOGGER.debug("BaseLight %s handling packet %s", self.name, packet)
        if len(packet) == 1:
            for attribute in COLOR_SOLO_UPDATES:
                if attribute in packet:
                    packet["switch"] = "1"

        self._light.update(packet)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on light."""
        _LOGGER.debug("Turn on %s %r", self.name, kwargs)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off light."""
        _LOGGER.debug("Turn off %s %r", self.name, kwargs)

    def on_message(self, _mqtt_client, _userdata, msg):
        """Handle a message from upstream."""
        packet = {}
        for item in json.loads(msg.payload):
            packet[item["type"]] = item["value"]

        self._handle_packet(packet)
        self.schedule_update_ha_state()

    def __repr__(self) -> str:
        return "<BaseLight name={!r} mode={!r} modes={!r} rgb={!r} temp={!r}>".format(
            self.name,
            self.color_mode,
            self.supported_color_modes,
            self.rgb_color,
            self.color_temp,
        )


class WhiteLight(BaseLight):
    """A Sengled wifi white light."""

    @property
    def color_temp(self) -> int | None:
        return 370  # 2700k, but per model?


class ColorLight(BaseLight):
    """A Sengled wifi color light."""

    # Figure out these ranges per light?
    # _attr_max_mireds = 370  # 1,000,000 divided by 2700 Kelvin = 370 Mireds
    # _attr_min_mireds = 154  # 1,000,000 divided by 6500 Kelvin = 154 Mireds

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return [int(rgbv) for rgbv in self._light["color"].split(":")]

    @property
    def color_temp(self) -> int | None:
        return percent_to_mireds(
            self._light["colorTemperature"],
            self._attr_min_mireds,
            self._attr_max_mireds,
        )

    @property
    def color_mode(self) -> ColorMode | str | None:
        if self._light["colorMode"] == "1":
            return ColorMode.RGB
        elif self._light["colorMode"] == "2":
            return ColorMode.COLOR_TEMP


class UnknownLight(Exception):
    """When we can't handle a light."""


def build_light(packet: DiscoveryInfoType) -> BaseLight:
    """Factory for bulbs."""
    match packet["typeCode"]:
        case "W21-N13":
            return ColorLight(packet)
        case "W21-N11":
            return WhiteLight(packet)
        case _:
            raise UnknownLight(str(packet))


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Sengled platform."""
    api = hass.data[DOMAIN]

    light = build_light(discovery_info)
    api.subscribe_light(light)
    _LOGGER.debug("Light built: %r", light)
    add_entities([light])
