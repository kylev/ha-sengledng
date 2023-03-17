"""Config Flow"""
import logging

from homeassistant.config_entries import ConfigFlow
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SengledNGConfigFlow(ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1

    @callback
    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        _LOGGER.debug("async_step_zeroconf %r", discovery_info)
        return self.async_abort(reason="Not implemented")
