"""SengledNG light platform."""
from __future__ import annotations

import json
import logging
import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    filter_supported_color_modes,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .api import API
from .const import ATTRIBUTION, DOMAIN

_LOGGER = logging.getLogger(__name__)

COLOR_TRANSLATIONS = {
    "brightness": ColorMode.BRIGHTNESS,
    "color": ColorMode.RGB,
    "colorTemperature": ColorMode.COLOR_TEMP,
}
COLOR_SOLO_UPDATES = {"brightness", "color"}


def decode_color_temp(value_pct: str, min_mireds: int, max_mireds: int) -> int:
    """Convert Sengled's brightness percentage to mireds given the light's range."""
    # return 370
    return math.ceil(
        max_mireds - ((int(value_pct) / 100.0) * (max_mireds - min_mireds))
    )


def encode_color_temp(value_mireds: int, min_mireds: int, max_mireds: int) -> str:
    """Convert brightness from HA to Sengled."""
    return str(math.ceil((value_mireds - min_mireds) / (max_mireds - min_mireds) * 100))


class BaseLight(LightEntity):
    """Base Light"""

    _light: DiscoveryInfoType = {}
    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False

    def __init__(self, api: API, info: DiscoveryInfoType) -> None:
        _LOGGER.debug("BaseLight init %r", info)
        self._api = api
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
        if len(packet) == 1 or packet.get("switch") == "1":
            packet["switch"] = "1"
            if "color" in packet:
                packet["colorMode"] = "1"
            if "colorTemperature" in packet:
                packet["colorMode"] = "2"

        self._light.update(packet)

    def turn_on(self, **kwargs: Any) -> None:
        """Turn on light."""
        _LOGGER.debug("Turn on %s %r", self.name, kwargs)

        message = {}
        if len(kwargs) == 0:
            message.update({"type": "switch", "value": "1"})
        if ATTR_BRIGHTNESS in kwargs:
            message.update(
                {"type": "brightness", "value": str(min(kwargs[ATTR_BRIGHTNESS], 100))}
            )
        if ATTR_RGB_COLOR in kwargs:
            message.update(
                {
                    "type": "color",
                    "value": ":".join([str(v) for v in kwargs[ATTR_RGB_COLOR]]),
                }
            )
        if ATTR_COLOR_TEMP in kwargs:
            message.update(
                {
                    "type": "colorTemperature",
                    "value": encode_color_temp(
                        kwargs[ATTR_COLOR_TEMP], self.min_mireds, self.max_mireds
                    ),
                }
            )  # TODO

        if len(message) == 0:
            _LOGGER.warning("Empty action from turn_on command: %r", kwargs)
        self._api.send_message(self.unique_id, message)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn off light."""
        _LOGGER.debug("Turn off %s %r", self.name, kwargs)
        self._api.send_message(self.unique_id, {"type": "switch", "value": "0"})

    def on_message(self, _mqtt_client, _userdata, msg):
        """Handle a message from upstream."""
        payload = json.loads(msg.payload)
        if not isinstance(payload, list):
            _LOGGER.warning("Strange message %r", payload)
            return

        packet = {}
        for item in payload:
            if len(item) == 0:
                continue
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
        return decode_color_temp(
            self._light["colorTemperature"],
            self.min_mireds,
            self.max_mireds,
        )

    @property
    def color_mode(self) -> ColorMode | str | None:
        if self._light["colorMode"] == "1":
            return ColorMode.RGB
        elif self._light["colorMode"] == "2":
            return ColorMode.COLOR_TEMP


class UnknownLight(Exception):
    """When we can't handle a light."""


def build_light(api: API, packet: DiscoveryInfoType) -> BaseLight:
    """Factory for bulbs."""
    match packet["typeCode"]:
        case "W21-N13":
            return ColorLight(api, packet)
        case "W21-N11":
            return WhiteLight(api, packet)
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

    light = build_light(api, discovery_info)
    api.subscribe_light(light)
    _LOGGER.debug("Light built: %r", light)
    add_entities([light])
