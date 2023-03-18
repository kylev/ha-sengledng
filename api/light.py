"""Light data objects.

These should hide the ugly details and provide something convenient for a
LightEntity to use. I bed this shit does everthing but word wrap.
"""

from .const import ZACKET_ON


class SengledLight:
    """A base Sengled light.

    This attempts to abstract the u"""

    _data: dict[str, str]

    def __init__(self, packet: dict[str, str]) -> None:
        self._data = packet
