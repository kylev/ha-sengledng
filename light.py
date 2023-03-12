"""SengledNG light platform."""
from __future__ import annotations

import logging

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import ATTRIBUTION, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BaseLight(LightEntity):
    """Base Light"""

    _attr_attribution = ATTRIBUTION
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(self, info: DiscoveryInfoType) -> None:
        self._attr_available = info["online"] == "1"
        self._attr_brightness = int(info["brightness"])

        self._attr_name = info["name"]
        self._unique_id = info["deviceUuid"]

        # self._sg_animations = info["deviceAnimations"]
        self._sg_category = info["category"]
        self._sg_type = info["typeCode"]

    # def __str__(self) -> str:
    #     return "Bulb {} ({}): {}".format(self._type, self._uuid, str(self._attributes))

    def update(self):
        """Fetch new data and update state."""
        _LOGGER.info("Update called")


class WhiteLight(BaseLight, LightEntity):
    """A Sengled wifi white light."""

    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}


COLOR_TRANSLATIONS = {
    "brightness": ColorMode.BRIGHTNESS,
    "color": ColorMode.RGB,
    "colorTemperature": ColorMode.COLOR_TEMP,
}


class ColorLight(BaseLight):
    """A Sengled wifi color light."""

    def __init__(self, info: DiscoveryInfoType) -> None:
        super().__init__(info)

        self._color_rgb = [int(rgbv) for rgbv in info["color"].split(":")]
        self._attr_supported_color_modes = set(
            [COLOR_TRANSLATIONS[k] for k in info["supportAttributes"].split(",")]
        )
        _LOGGER.warning("Yays %s", self._attr_supported_color_modes)


class UnknownLight(Exception):
    """When we can't handle a light."""


def build_light(packet: DiscoveryInfoType) -> BaseLight:
    """Factory for bulbs."""
    _LOGGER.debug("Building light %s", packet)
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
    _LOGGER.warning("Entered light setup platform for %s %s", DOMAIN, discovery_info)

    add_entities([build_light(discovery_info)])
