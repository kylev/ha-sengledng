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

from .api import API, create_light, encode_color_temp
from .const import (
    ATTRIBUTION,
    DOMAIN,
    PACKET_BRIGHTNESS,
    PACKET_RGB_COLOR,
    PACKET_EFFECT,
    PACKET_VALUE_ON,
    PACKET_VALUE_OFF,
    PACKET_SWITCH,
    PACKET_COLOR_TEMP,
)

_LOGGER = logging.getLogger(__name__)

COLOR_TRANSLATIONS = {
    "brightness": ColorMode.BRIGHTNESS,
    "color": ColorMode.RGB,
    "colorTemperature": ColorMode.COLOR_TEMP,
}


class Light(LightEntity):
    """Base Light"""

    _light: DiscoveryInfoType = {}
    _attr_attribution = ATTRIBUTION
    _attr_should_poll = False

    def __init__(self, api: API, info: DiscoveryInfoType) -> None:
        _LOGGER.debug("BaseLight init %r", info)
        self._api = api
        self._light = create_light(info)

    unique_id = property(lambda s: s._light.unique_id)
    name = property(lambda s: s._light.name)
    mqtt_topics = property(lambda s: s._light.mqtt_topics)

    available = property(lambda s: s._light.available)
    brightness = property(lambda s: s._light.brightness)
    color_mode = property(lambda s: s._light.color_mode)
    color_temp = property(lambda s: s._light.color_temp)
    effect_list = property(lambda s: s._light.effect_list)
    is_on = property(lambda s: s._light.is_on)
    rgb_color = property(lambda s: s._light.rgb_color)

    @property
    def supported_color_modes(self) -> set[ColorMode] | set[str] | None:
        return filter_supported_color_modes(
            [COLOR_TRANSLATIONS[k] for k in self._light.supported_color_modes]
        )

    @property
    def supported_features(self) -> LightEntityFeature:
        sengled_features = 0
        if len(self.effect_list):
            sengled_features |= LightEntityFeature.EFFECT
        return super().supported_features | sengled_features

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            manufacturer="Sengled",
            model=self._light.model,
            sw_version=self._light.sw_version,
        )

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
        if ATTR_EFFECT in kwargs:
            value = PACKET_VALUE_ON
            if effect == "none":
                effect = self.effect
                value = PACKET_VALUE_OFF
            messages.append({"type": effect, "value": value})

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

    @property
    def effect(self) -> str | None:
        return {
            "1": "colorCycle",
            "2": "randomColor",
            "3": "rhythm",
            "4": "christmas",
            "5": "halloween",
            "6": "festival",
        }.get(self._light.get(PACKET_EFFECT, None), None)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Sengled platform."""
    api = hass.data[DOMAIN]

    light = Light(api, discovery_info)
    await api.async_register_light(light)
    add_entities([light])
    _LOGGER.info("Discovered light %r", light)
