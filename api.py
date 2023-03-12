"""API immplmentation for SengledNG"""
from http import HTTPStatus
import logging
import uuid

import async_timeout
import paho.mqtt.client as mqtt

from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

import uuid

import aiohttp
import paho.mqtt.client as mqtt
from typing import Any, List

from homeassistant.helpers.typing import DiscoveryInfoType

from .light import build_light

_LOGGER = logging.getLogger(__name__)


def _hassify_discovery(packet: dict[str, Any]) -> DiscoveryInfoType:
    result: DiscoveryInfoType = {}
    for k, v in packet.items():
        if isinstance(v, str):
            result[k] = v
        elif k in {"attributeList", "deviceAnimations"}:
            pass
        else:
            _LOGGER.warning("Weird value while hassifying: %s", (k, v))

    for item in packet["attributeList"]:
        result[item["name"]] = item["value"]

    return result


class AuthError(Exception):
    """Something went wrong with login."""


class API:
    """API for Sengled"""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._cookiejar = aiohttp.CookieJar()
        self._http = aiohttp.ClientSession(cookie_jar=self._cookiejar)
        self._jsession_id: str = None

    async def async_setup(self):
        await self._async_login()

    async def _async_login(self):
        url = "https://ucenter.cloud.sengled.com/user/app/customer/v2/AuthenCross.json"
        # For Zigbee? login_path = "/zigbee/customer/login.json"
        payload = {
            "uuid": uuid.uuid4().hex[:-16],
            "user": self._username,
            "pwd": self._password,
            "osType": "android",
            "productCode": "life",
            "appCode": "life",
        }

        async with self._http.post(url, json=payload) as resp:
            if resp.status != 200:
                raise AuthError(resp.headers)
            data = await resp.json()
            if data["ret"] != 0:
                raise AuthError("Login failed: {}".format(data["msg"]))
            self._jsession_id = data["jsessionId"]

    async def _async_get_server_info(self):
        """Get secondary server info from the primary."""
        url = "https://life2.cloud.sengled.com/life2/server/getServerInfo.json"
        async with self._http.post(url) as resp:
            data = await resp.json()
            self._jbalancer_url = data["jbalancerAddr"]
            self._inception_url = data["inceptionAddr"]

    async def async_list_devices(self) -> List[DiscoveryInfoType]:
        url = "https://life2.cloud.sengled.com/life2/device/list.json"
        async with self._http.post(url) as resp:
            data = await resp.json()
            # _LOGGER.debug("Incoming async_list_devices data %s", data)
            # return [_hassify_discovery(d) for d in data["deviceList"]]
            return [_hassify_discovery(d) for d in data["deviceList"]]

    async def shutdown(self):
        await self._http.close()
