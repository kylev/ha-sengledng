"""API implmentation for SengledNG"""
import aiohttp
from http import HTTPStatus
import json
import logging
import time
from typing import Any
from urllib import parse
import uuid

from paho.mqtt import client as mqtt

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

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password
        self._cookiejar = aiohttp.CookieJar()
        self._http = aiohttp.ClientSession(cookie_jar=self._cookiejar)
        self._mqtt = mqtt.Client(transport="websockets")

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
            self._jbalancer_url = parse.urlparse(data["jbalancerAddr"])
            self._inception_url = parse.urlparse(data["inceptionAddr"])

    async def _async_setup_mqtt(self):
        """Setup up MQTT client."""
        _LOGGER.debug(
            "MQTT setup with %s %r",
            self._jsession_id,
            self._inception_url,
        )

        self._mqtt = mqtt.Client(
            client_id="{}@lifeApp".format(self._jsession_id),
            transport="websockets",
        )

        def on_connect(client, _userdata, flags, result_code):
            _LOGGER.info(
                "MQTT connected with result code %s %s",
                flags,
                mqtt.connack_string(result_code),
            )
            client.subscribe("$SYS/#")
            # client.subscribe("wifielement/#")  # Yikes
            # Why don't these work? Special syntax for their server?
            # client.subscribe("wifielement/+/status")
            # client.subscribe("wifielement/+/consumption")
            # client.subscribe("wifielement/+/consumptionTime")

        def on_connect_fail(_client, _userdata):
            _LOGGER.warning("MQTT connection failed")

        def on_disconnect(_client, _userdata, result_code):
            _LOGGER.warning("MQTT disconnected: %s", mqtt.error_string(result_code))

        def on_subscribe(_client, _userdata, mid, _granted_qos):
            _LOGGER.debug("MQTT subscribed MID:%s", mid)

        def on_message(_client, _userdata, msg):
            if msg.topic.startswith("SYS"):
                payload = json.loads(msg.payload)
                _LOGGER.warning("MQTT system message(%s): %r", msg.topic, payload)

        self._mqtt.on_connect = on_connect
        self._mqtt.on_connect_fail = on_connect_fail
        self._mqtt.on_disconnect = on_disconnect
        self._mqtt.on_message = on_message
        self._mqtt.on_subscribe = on_subscribe
        self._mqtt.ws_set_options(
            path=self._inception_url.path,
            headers={
                "Cookie": "JSESSIONID={}".format(self._jsession_id),
                "X-Requested-With": "com.sengled.life2",
            },
        )
        self._mqtt.tls_set_context()
        self._mqtt.enable_logger()

        # TODO Figure out how to use connect_async() without sometimes swallowing the first subscribe calls...
        self._mqtt.connect(self._inception_url.hostname, self._inception_url.port)
        self._mqtt.loop_start()

    async def async_list_devices(self) -> list[DiscoveryInfoType]:
        """Get a list of HASS-friendly discovered devices."""
        url = "https://life2.cloud.sengled.com/life2/device/list.json"
        async with self._http.post(url) as resp:
            data = await resp.json()
            return [_hassify_discovery(d) for d in data["deviceList"]]

    def subscribe_light(self, light):
        """Subscribe a light to its updates."""
        self._mqtt.message_callback_add(
            "wifielement/{}/#".format(light.unique_id), light.on_message
        )
        self._mqtt.subscribe("wifielement/{}/update".format(light.unique_id))
        # self._mqtt.subscribe("wifielement/{}/consumption".format(light.unique_id))
        # self._mqtt.subscribe("wifielement/{}/consumptionTime".format(light.unique_id))

    def send_message(self, device_id: str, message: Any):
        """Send a MQTT message to central control."""
        message.update({"dn": device_id, "time": int(time.time() * 1000)})
        self._mqtt.publish(
            "wifielement/{}/update".format(device_id),
            json.dumps([message]),
        )

    async def shutdown(self):
        """Shutdown and tidy up."""
        await self._http.close()
