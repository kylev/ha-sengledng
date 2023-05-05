"""Zigbee bulb implementations.

Sengled SmartHub is listening on 8686.
AT+GW_COOR_GET_ALL_LAMP_STATUS
"""
from __future__ import annotations

import math
from typing import Final

from .api_bulb import APIBulb

DEVICE_ATTRIBUTES: Final = "attributes"


class ZigbeeBulb(APIBulb):
    """A white bulb."""

    def __init__(self, discovery) -> None:
        self._data = discovery

    def __repr__(self) -> str:
        return "<{} {!r}>".format(self.__class__.__name__, self._data)

    @property
    def unique_id(self):
        return self._data["deviceUuid"]

    @property
    def name(self):
        return self._data[DEVICE_ATTRIBUTES]["name"]

    @property
    def available(self) -> bool:
        """Is the light available."""
        return self._data[DEVICE_ATTRIBUTES]["isOnline"] == "1"

    @property
    def is_on(self) -> bool:
        return self._data[DEVICE_ATTRIBUTES]["onoff"] == "1"

    @property
    def brightness(self) -> int | None:
        return math.ceil(int(self._data[DEVICE_ATTRIBUTES]["brightness"]) / 100 * 255)

    @property
    def sw_version(self) -> str:
        return self._data[DEVICE_ATTRIBUTES]["version"]

    @property
    def model(self) -> str:
        return self._data[DEVICE_ATTRIBUTES]["productCode"]

    @property
    def mqtt_topics(self) -> list[str]:
        # uid = self.unique_id
        # n = 2
        # chunks = [uid[i : i + n] for i in range(0, len(uid), n)]
        # return [
        #     "sengled/{}/status".format(uid),
        #     "sengled/{}/status".format(":".join(chunks)),
        # ]
        return []


class ZigbeeColorBulb(ZigbeeBulb):
    """A color bulb."""
