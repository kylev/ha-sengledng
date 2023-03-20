"""Config Flow"""
import logging

from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

import voluptuous as vol

from .api import API, AuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SengledNGConfigFlow(ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1

    @callback
    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}
        if user_input is not None:
            try:
                await API.check_auth(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
                return self.async_create_entry(title=DOMAIN, data=user_input)
            except AuthError:
                errors["base"] = "Login failed"

        data_schema = {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )

    @callback
    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        _LOGGER.debug("async_step_zeroconf %r", discovery_info)
        return self.async_abort(reason="Not implemented")
