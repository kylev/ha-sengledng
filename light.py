"""SengledNG light platform."""
from __future__ import annotations

import json
import logging
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


class BaseLight(LightEntity):
    """Base Light"""

    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False

    def __init__(self, info: DiscoveryInfoType) -> None:
        _LOGGER.debug("BaseLight init %r", info)
        self._device_id = info["deviceUuid"]
        self._attr_unique_id = info["deviceUuid"]

        self._attr_name = info["name"]
        self._attr_supported_color_modes = filter_supported_color_modes(
            [COLOR_TRANSLATIONS[k] for k in info["supportAttributes"].split(",")]
        )
        self._attr_device_info = DeviceInfo(
            manufacturer="Sengled", model=info["typeCode"], sw_version=info["version"]
        )

        self._store_stuff(info)

    def update(self):
        """Fetch new data and update state."""
        _LOGGER.debug("Update %s", self.name)

    def _store_stuff(self, info):
        """Update state"""
        _LOGGER.error("Base store %s", info)

        if "online" in info:
            self._attr_available = info["online"] == "1"
        if "brightness" in info:
            self._attr_brightness = int(info["brightness"])
        if "switch" in info:
            self._attr_is_on = info["switch"] == "1"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on light."""
        _LOGGER.debug("Turn on %s", self.name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off light."""
        _LOGGER.debug("Turn off %s", self.name)

    def on_message(self, _mqtt_client, _userdata, msg):
        """Handle a message from upstream."""
        # _LOGGER.debug("Bulb(%s) message %s", self.name, msg)
        packet = {}
        for item in json.loads(msg.payload):
            packet[item["type"]] = item["value"]
        self._store_stuff(packet)
        self.schedule_update_ha_state()
        _LOGGER.debug("Bulb(%s) message %s", self.name, packet)

    def __repr__(self) -> str:
        return "<BaseLight name={!r} mode={!r} modes={!r} rgb={!r} temp={!r}>".format(
            self._attr_name,
            self._attr_color_mode,
            self._attr_supported_color_modes,
            self._attr_rgb_color,
            self._attr_color_temp,
        )


class WhiteLight(BaseLight):
    """A Sengled wifi white light."""

    _attr_color_temp = 370  # 2700k, but per model?


class ColorLight(BaseLight):
    """A Sengled wifi color light."""

    # Figure out these ranges per light?
    # _attr_max_mireds = 370  # 1,000,000 divided by 2700 Kelvin = 370 Mireds
    # _attr_min_mireds = 154  # 1,000,000 divided by 6500 Kelvin = 154 Mireds

    def __init__(self, info: DiscoveryInfoType) -> None:
        super().__init__(info)

        self._attr_color_temp = self._attr_max_mireds - (
            (int(info["colorTemperature"]) / 100.0)
            * (self._attr_max_mireds - self._attr_min_mireds)
        )

    def _store_stuff(self, info):
        super()._store_stuff(info)
        _LOGGER.error("Color store %s", info)

        if "color" in info:
            self._attr_rgb_color = [int(rgbv) for rgbv in info["color"].split(":")]
        if "colorMode" in info:
            if info["colorMode"] == "1":
                self._attr_color_mode = ColorMode.RGB
            elif info["colorMode"] == "2":
                self._attr_color_mode = ColorMode.COLOR_TEMP


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
    # _LOGGER.warning("Entered light setup platform for %s %s", DOMAIN, discovery_info)
    api = hass.data[DOMAIN]

    light = build_light(discovery_info)
    api.subscribe_light(light)
    _LOGGER.warning("Light built: %s", light)
    add_entities([light])
