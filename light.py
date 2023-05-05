"""SengledNG light platform."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .api import ElementsBulb, ElementsColorBulb, ZigbeeBulb
from .const import ATTRIBUTION, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ElementsLightEntity(ElementsBulb, LightEntity):
    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False

    def __init__(self, api, discovery) -> None:
        super().__init__(discovery)
        self._api = api

    def update_bulb(self, payload):
        super().update_bulb(payload)
        self.schedule_update_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn off light."""
        _LOGGER.debug("Turn on %s %r", self.name, kwargs)
        if len(kwargs) == 0:
            await self.set_power(True)
        if ATTR_BRIGHTNESS in kwargs:
            await self.set_brightness(kwargs[ATTR_BRIGHTNESS])
        if ATTR_RGB_COLOR in kwargs:
            await self.set_color(kwargs[ATTR_RGB_COLOR])
        if ATTR_COLOR_TEMP in kwargs:
            await self.set_temperature(kwargs[ATTR_COLOR_TEMP])
        if ATTR_EFFECT in kwargs:
            effect = kwargs[ATTR_EFFECT]
            enable = True
            if effect == "none":
                effect = self.effect
                enable = False
            await self.set_effect(effect, enable)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off light."""
        _LOGGER.debug("Turn off %s %r", self.name, kwargs)
        await self.set_power(False)

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer="Sengled",
            model=self.model,
            sw_version=self.sw_version,
        )

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        return {ColorMode.BRIGHTNESS}

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


class ElementsColorLightEntity(ElementsColorBulb, ElementsLightEntity):
    @property
    def supported_features(self) -> LightEntityFeature:
        return LightEntityFeature.EFFECT

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        return {ColorMode.BRIGHTNESS, ColorMode.COLOR_TEMP, ColorMode.RGB}


class ZigbeeLightEntity(ZigbeeBulb, LightEntity):
    """A bulb."""

    def __init__(self, api, discovery) -> None:
        super().__init__(discovery)
        self._api = api


def pick_light(discovery: DiscoveryInfoType):
    """Pick which light implementation to use."""
    if "typeCode" in discovery:
        if discovery["typeCode"] == "W21-N13":
            return ElementsColorLightEntity
        if discovery["typeCode"] == "W21-N11":
            return ElementsLightEntity
    if "supportAttributes" in discovery:
        return ZigbeeLightEntity
    return None


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Sengled platform."""
    api = hass.data[DOMAIN]

    clazz = pick_light(discovery_info)
    if clazz is None:
        _LOGGER.warning("Unsupported device discovered: %r", discovery_info)
        return
    light = clazz(api, discovery_info)
    await api.async_register_light(light)
    add_entities([light])
    _LOGGER.info("Discovered light %r", light)
