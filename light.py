"""SengledNG light platform."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import ATTRIBUTION, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BaseLight(LightEntity):
    """Base Light"""

    _attr_attribution = ATTRIBUTION
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_max_mireds = 370  # 1,000,000 divided by 2700 Kelvin = 370 Mireds
    _attr_min_mireds = 154  # 1,000,000 divided by 6500 Kelvin = 154 Mireds

    def __init__(self, info: DiscoveryInfoType) -> None:
        self._unique_id = info["deviceUuid"]

        self._attr_available = info["online"] == "1"
        self._attr_brightness = int(info["brightness"])
        self._attr_is_on = info["switch"] == "1"
        self._attr_name = info["name"]
        self._attr_supported_color_modes = set(
            [COLOR_TRANSLATIONS[k] for k in info["supportAttributes"].split(",")]
        )
        self._attr_device_info = DeviceInfo(
            manufacturer="Sengled", model=info["typeCode"], sw_version=info["version"]
        )

    def update(self):
        """Fetch new data and update state."""
        _LOGGER.info("Update called")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on light."""
        _LOGGER.info("Turn on?")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off light."""
        _LOGGER.info("Turn off?")


class WhiteLight(BaseLight):
    """A Sengled wifi white light."""


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
        self._attr_color_temperature = 154 + (216 * int(info["colorTemperature"]) / 100.0)
        if info["colorMode"] == "2":
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif info["colorMode"] == "1":
            self._attr_color_mode = ColorMode.RGB

        _LOGGER.warning("Yays %s", self._color_rgb)


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
