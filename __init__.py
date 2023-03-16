"""A next-gen integration for Sengled lights."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import API
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)
PLATFORMS = [Platform.LIGHT]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the platform API."""
    _LOGGER.info("Setup SengledNG package")

    api = API(hass, config[DOMAIN][CONF_USERNAME], config[DOMAIN][CONF_PASSWORD])
    hass.data[DOMAIN] = api
    hass.async_create_background_task(api.async_start(), "SengledNG")

    return True
