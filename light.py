"""SengledNG light platform."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
    filter_supported_color_modes,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .api import API
from .const import (
    ATTRIBUTION,
    DOMAIN,
    PACKET_BRIGHTNESS,
    PACKET_COLOR_MODE,
    PACKET_COLOR_TEMP,
    PACKET_EFFECT,
    PACKET_ONLINE,
    PACKET_RGB_COLOR,
    PACKET_SWITCH,
    PACKET_VALUE_OFF,
    PACKET_VALUE_ON,
)

_LOGGER = logging.getLogger(__name__)

COLOR_TRANSLATIONS = {
    "brightness": ColorMode.BRIGHTNESS,
    "color": ColorMode.RGB,
    "colorTemperature": ColorMode.COLOR_TEMP,
}


def decode_color_temp(value_pct: str, min_mireds: int, max_mireds: int) -> int:
    """Convert Sengled's brightness percentage to mireds given the light's range."""
    # return 370
    return math.ceil(
        max_mireds - ((int(value_pct) / 100.0) * (max_mireds - min_mireds))
    )


def encode_color_temp(value_mireds: int, min_mireds: int, max_mireds: int) -> str:
    """Convert brightness from HA to Sengled."""
    return str(math.ceil((max_mireds - value_mireds) / (max_mireds - min_mireds) * 100))


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
    def mqtt_topics(self) -> tuple[str]:
        """The topic."""
        # Wish I could do "wifielement/{}/consumptionTime"
        return tuple(
            "wifielement/{}/status".format(self.unique_id),
        )

    @property
    def is_on(self) -> bool | None:
        return self._light[PACKET_SWITCH] == PACKET_VALUE_ON

    @property
    def available(self) -> bool:
        return self._light[PACKET_ONLINE] == PACKET_VALUE_ON

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        return filter_supported_color_modes(
            [COLOR_TRANSLATIONS[k] for k in self._light["supportAttributes"].split(",")]
        )

    @property
    def brightness(self) -> int | None:
        return math.ceil(int(self._light[PACKET_BRIGHTNESS]) / 100 * 255)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on light."""
        _LOGGER.debug("Turn on %s %r", self.name, kwargs)

        if len(kwargs) == 0:
            await self._async_send_update(PACKET_SWITCH, PACKET_VALUE_ON)
            return

        messages = []
        if ATTR_BRIGHTNESS in kwargs:
            messages.append(
                {
                    "type": PACKET_BRIGHTNESS,
                    "value": str(math.ceil(kwargs[ATTR_BRIGHTNESS] / 255 * 100)),
                }
            )
        if ATTR_RGB_COLOR in kwargs:
            messages.append(
                {
                    "type": PACKET_RGB_COLOR,
                    "value": ":".join([str(v) for v in kwargs[ATTR_RGB_COLOR]]),
                }
            )
        if ATTR_COLOR_TEMP in kwargs:
            messages.append(
                {
                    "type": PACKET_COLOR_TEMP,
                    "value": encode_color_temp(
                        kwargs[ATTR_COLOR_TEMP], self.min_mireds, self.max_mireds
                    ),
                }
            )

        if len(messages) == 0:
            _LOGGER.warning("Empty action from turn_on command: %r", kwargs)
        else:
            await self._api.async_send_updates(self.unique_id, *messages)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off light."""
        _LOGGER.debug("Turn off %s %r", self.name, kwargs)
        await self._async_send_update(PACKET_SWITCH, PACKET_VALUE_OFF)

    def update_light(self, packet):
        """Update state"""
        _LOGGER.debug("Packet %s %s", packet, self)
        self._light.update(packet)
        self.schedule_update_ha_state()

    async def _async_send_update(self, update_type: str, value: str):
        await self._api.async_send_updates(
            self.unique_id, {"type": update_type, "value": value}
        )

    def __repr__(self) -> str:
        return "<{} name={!r} brightness={!r} rgb={!r} mode={} supported_modes={!r} temp={!r}>".format(
            self.__class__.__name__,
            self.name,
            self.brightness,
            self.rgb_color,
            self.color_mode,
            self.supported_color_modes,
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
    # 1,000,000 divided by 2700 Kelvin = 370 Mireds
    _attr_max_mireds = 400
    # _attr_min_mireds = 154  # 1,000,000 divided by 6500 Kelvin = 154 Mireds

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return tuple(int(rgb) for rgb in self._light[PACKET_RGB_COLOR].split(":"))

    @property
    def color_temp(self) -> int | None:
        return decode_color_temp(
            self._light[PACKET_COLOR_TEMP],
            self.min_mireds,
            self.max_mireds,
        )

    @property
    def color_mode(self) -> ColorMode | str | None:
        match self._light[PACKET_COLOR_MODE]:
            case "1":
                return ColorMode.RGB
            case "2":
                return ColorMode.COLOR_TEMP

    @property
    def supported_features(self) -> LightEntityFeature:
        return super().supported_features | LightEntityFeature.EFFECT

    @property
    def effect(self) -> str | None:
        return {
            "1": "colorCycle",
            "2": "randomColor",
            "3": "rhythm",
            "4": "christmas",
            "5": "halloween",
            "6": "festival",
        }.get(self._light[PACKET_EFFECT], None)

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        effect = kwargs.pop(ATTR_EFFECT, None)
        if effect:
            value = PACKET_VALUE_ON
            if effect == "none":
                effect = self.effect
                value = PACKET_VALUE_OFF
            await self._async_send_update(effect, value)
        await super().async_turn_on(**kwargs)


class UnknownLight(Exception):
    """When we can't handle a light."""


def build_light(api: API, packet: DiscoveryInfoType) -> BaseLight:
    """Factory for bulbs."""
    if PACKET_RGB_COLOR in packet:
        return ColorLight(api, packet)
    if PACKET_BRIGHTNESS in packet:
        return WhiteLight(api, packet)

    _LOGGER.warning("Couldn't build light for packet %s", packet)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Sengled platform."""
    api = hass.data[DOMAIN]

    light = build_light(api, discovery_info)
    await api.async_register_light(light)
    add_entities([light])
    _LOGGER.info("Discovered light %r", light)
