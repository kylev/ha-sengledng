"""API implmentation for SengledNG"""
import aiohttp
from http import HTTPStatus
import json
import logging
import time
from typing import Any
from urllib import parse
import uuid

import asyncio_mqtt as mqtt
import ssl

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import DiscoveryInfoType


_LOGGER = logging.getLogger(__name__)


def _hassify_discovery(packet: dict[str, Any]) -> DiscoveryInfoType:
    result: DiscoveryInfoType = {}
    for key, value in packet.items():
        if key in {"attributeList"}:
            continue

        if isinstance(value, str) or isinstance(value, list):
            result[key] = value
        else:
            _LOGGER.warning("Weird value while hass-ifying: %s", (key, value))

    for item in packet["attributeList"]:
        result[item["name"]] = item["value"]

    return result


class AuthError(Exception):
    """Something went wrong with login."""


class API:
    """API for Sengled"""

    _inception_url: parse.ParseResult | None = None
    _jbalancer_url: parse.ParseResult | None = None
    _jsession_id: str | None = None
    _lights = {}
    _mqtt: mqtt.Client | None = None

    def __init__(self, hass: HomeAssistant, username: str, password: str) -> None:
        self._hass = hass
        self._username = username
        self._password = password
        self._cookiejar = aiohttp.CookieJar()
        self._http = aiohttp.ClientSession(cookie_jar=self._cookiejar)

    async def async_setup(self):
        """Perform setup."""
        await self._async_login()
        await self._async_get_server_info()
        await self._async_setup_mqtt()

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
            if resp.status != HTTPStatus.OK:
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
            _LOGGER.debug("Raw server info %r", data)
            self._jbalancer_url = parse.urlparse(data["jbalancerAddr"])
            self._inception_url = parse.urlparse(data["inceptionAddr"])

    async def _async_setup_mqtt(self):
        """Setup up MQTT client."""
        self._mqtt = mqtt.Client(
            self._inception_url.hostname,
            self._inception_url.port,
            client_id="{}@lifeApp".format(self._jsession_id),
            tls_context=ssl.create_default_context(),
            transport="websockets",
            websocket_headers={
                "Cookie": "JSESSIONID={}".format(self._jsession_id),
                "X-Requested-With": "com.sengled.life2",
            },
            websocket_path=self._inception_url.path,
        )

        await self._mqtt.connect()

    async def async_list_devices(self) -> list[DiscoveryInfoType]:
        """Get a list of HASS-friendly discovered devices."""
        url = "https://life2.cloud.sengled.com/life2/device/list.json"
        async with self._http.post(url) as resp:
            data = await resp.json()
            return [_hassify_discovery(d) for d in data["deviceList"]]

    async def async_start(self):
        """Start the API's main event loop."""
        async with self._mqtt.messages() as messages:
            async for message in messages:
                if message.topic.matches("wifielement/+/status"):
                    self._lights[message.topic.value.split("/")[1]].on_message(message)
                elif message.topic.matches("wifielement/+/update"):
                    pass  # Ignore our own
                else:
                    _LOGGER.info("Dropping: %s %r", message.topic, message.payload)

    async def subscribe_light(self, light):
        """Subscribe a light to its updates."""
        self._lights[light.unique_id] = light
        await self._mqtt.subscribe("wifielement/{}/#".format(light.unique_id))
        # await self._mqtt.subscribe("wifielement/{}/#".format(light.unique_id))
        # await self._mqtt.subscribe("wifielement/{}/update".format(light.unique_id))
        # await self._mqtt.subscribe("wifielement/{}/consumption".format(light.unique_id))
        # await self._mqtt.subscribe(
        #     "wifielement/{}/consumptionTime".format(light.unique_id)
        # )

    async def async_send_message(self, device_id: str, message: Any):
        """Send a MQTT message to central control."""
        message.update({"dn": device_id, "time": int(time.time() * 1000)})
        await self._mqtt.publish(
            "wifielement/{}/update".format(device_id),
            payload=json.dumps([message]),
        )

    async def shutdown(self):
        """Shutdown and tidy up."""
        await self._http.close()
