"""API immplmentation for SengledNG"""
import logging
import uuid
from http import HTTPStatus

import async_timeout
import paho.mqtt.client as mqtt

from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class AuthError(Exception):
    """Auth failed"""


class CloudAPI:
    """The API."""

    def __init__(self, hass: HomeAssistant, username: str, password: str) -> None:
        self.hass = hass

        self._username = username
        self._password = password
        # self._cookies = {}
        self._jsession_id = None

    async def async_login(self):
        """Login"""
        result = await self._async_freshen_login()
        _LOGGER.warning("SengledNG login result %s cookies", result)
        return result

    async def _async_freshen_login(self):
        # "https://ucenter.cloud.sengled.com/user/app/customer/v2/AuthenCross.json"
        base_url = "https://ucenter.cloud.sengled.com"
        login_path = "/user/app/customer/v2/AuthenCross.json"
        # login_path = "/zigbee/customer/login.json"
        payload = {
            "uuid": uuid.uuid4().hex[:-16],
            "user": self._username,
            "pwd": self._password,
            "osType": "android",
            "productCode": "life",
            "appCode": "life",
        }

        _LOGGER.warning("Logging in with %s", str(payload))

        websession = async_create_clientsession(self.hass, base_url=base_url)
        async with async_timeout.timeout(10):
            result = await websession.post(login_path, json=payload)
            _LOGGER.warning(
                "Response headers %s cookies %s", result.headers, websession.cookie_jar
            )
            if result.status != HTTPStatus.OK:
                raise AuthError("Unexpected server response {}".format(result.status))

            data = await result.json()
            _LOGGER.warning("Got back %s", str(data))
            if data["ret"] != 0:
                _LOGGER.error("Not ok %s", str(data))
                raise AuthError(data)

            self._jsession_id = data["jsessionId"]
            return data

    def do_stuff(self):
        """Load client as property?"""
        return mqtt.Client(self._jsession_id)
