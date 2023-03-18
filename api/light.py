"""Light data objects.

These should hide the ugly details and provide something convenient for a
LightEntity to use. I bed this shit does everthing but word wrap.
"""
from __future__ import annotations

from collections import UserDict # TODO Aspire to remove.
import logging
from typing import Any

from .const import PACKET_VALUE_ON, PACKET_ONLINE

_LOGGER = logging.getLogger(__name__)


def create_light(discovery: Any) -> SengledLight:
    """Create the appropriate API light for the discovery packet."""
    return SengledLight(discovery)


class SengledLight(UserDict):
    """A base Sengled light."""

    @property
    def available(self) -> bool:
        """Is the light available."""
        return self[PACKET_ONLINE] == PACKET_VALUE_ON
