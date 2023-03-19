"""API implmentation for SengledNG"""
import asyncio
from http import HTTPStatus
import json
import logging
import ssl
import time
from typing import Any
from urllib import parse
import uuid

import aiohttp
import asyncio_mqtt as mqtt

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import DiscoveryInfoType

from ..const import DOMAIN

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
    _mqtt: mqtt.Client | None = None

    def __init__(self, hass: HomeAssistant, username: str, password: str) -> None:
        self._hass = hass
        self._username = username
        self._password = password

        self._lights = {}
        self._lights_mutex = asyncio.Lock()
        self._cookiejar = aiohttp.CookieJar()
        self._http = aiohttp.ClientSession(cookie_jar=self._cookiejar)

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
        _LOGGER.info("Authentication completed")

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
        client = mqtt.Client(
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

        await client.connect()
        self._mqtt = client

        async with self._lights_mutex:
            lights = tuple(self._lights.values())
        for light in lights:
            await self._subscribe_light(light)
        _LOGGER.info("MQTT client ready")

    async def _async_discover_lights(self) -> list[DiscoveryInfoType]:
        """Get a list of HASS-friendly discovered devices."""
        url = "https://life2.cloud.sengled.com/life2/device/list.json"
        async with self._http.post(url) as resp:
            data = await resp.json()
            for device in [_hassify_discovery(d) for d in data["deviceList"]]:
                self._hass.helpers.discovery.load_platform(
                    Platform.LIGHT, DOMAIN, device, {}
                )

    async def async_start(self):
        """Start the API's main event loop."""
        await self._async_login()
        await self._async_get_server_info()
        await self._async_discover_lights()

        while True:
            try:
                await self._async_setup_mqtt()
                await self._message_loop()
            except mqtt.error.MqttConnectError as conerr:
                _LOGGER.info("MQTT refused, reauthenticating %r", conerr)
                await self._async_login()
            except mqtt.MqttError as error:
                _LOGGER.info("MQTT error, reconnecting %r", error)
                await asyncio.sleep(10)

    async def _message_loop(self):
        async with self._mqtt.messages() as messages:
            async for message in messages:
                if message.topic.matches("wifielement/+/status"):
                    self._handle_status(message)
                elif message.topic.matches("wifielement/+/update"):
                    pass
                else:
                    _LOGGER.warning("Dropping: %s %r", message.topic, message.payload)

    async def async_register_light(self, light):
        """Subscribe a light to its updates."""
        async with self._lights_mutex:
            self._lights[light.unique_id] = light
        await self._subscribe_light(light)

    async def _subscribe_light(self, light):
        if self._mqtt:
            for topic in light.mqtt_topics:
                await self._mqtt.subscribe(topic)

    async def async_send_updates(self, device_id: str, *messages: list[dict[str, str]]):
        """Send a MQTT update to central control."""
        extras = {"dn": device_id, "time": int(time.time() * 1000)}

        await self._mqtt.publish(
            "wifielement/{}/update".format(device_id),
            payload=json.dumps([message | extras for message in messages]),
        )
        _LOGGER.debug("MQTT publish %r", messages)

    def _handle_status(self, msg):
        """Handle a message from upstream."""
        light_id = msg.topic.value.split("/")[1]
        light = self._lights.get(light_id, None)
        if not light:
            _LOGGER.warning("Status for unknown light %s", light_id)
            return

        payload = json.loads(msg.payload)
        if not isinstance(payload, list):
            _LOGGER.warning("Strange message %r", payload)
            return

        packet = {}
        for item in payload:
            if len(item) == 0:
                continue
            packet[item["type"]] = item["value"]
        light.update_light(packet)

    async def shutdown(self):
        """Shutdown and tidy up."""
        await self._http.close()
