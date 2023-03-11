"""SengledNG light platform."""
from __future__ import annotations

import logging

from homeassistant.components.light import LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN

_LOGGER = logging.Logger(__name__)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Sengled platform."""
    _LOGGER.warning("Entered ligt setup platform for %s %s", DOMAIN, discovery_info)
    add_entities([])


class SengledLight(LightEntity):
    """A Sengled Light."""

    def update(self):
        """Fetch new data and update state."""
