"""The interface expected by API."""
from typing import Any


class APIBulb:
    def update_bulb(self, payload: Any) -> None:
        """Deliver an update packet to the bulb."""
        raise NotImplementedError("Bulbs must implement update_bulb")

    async def set_brightness(self, value: int) -> None:
        """Set the brightness."""
        raise NotImplementedError("Bulbs must implement set_brightness")

    async def set_color(self, value: tuple[int, int, int]) -> None:
        """Set the color in RGB."""
        raise NotImplementedError("Bulbs must implement set_color")

    async def set_effect(self, effect: str, enable: bool) -> None:
        """Set special effect."""
        raise NotImplementedError("Bulbs must implement set_effect")

    async def set_power(self, to_on=True) -> None:
        """Set the power on/off."""
        raise NotImplementedError("Bulbs must implement set_power")

    async def set_temperature(self, value: int) -> None:
        """Set the color temperature in minreds."""
        raise NotImplementedError("Bulbs must implement set_temperature")

    @property
    def mqtt_topics(self) -> list[str]:
        raise NotImplementedError("Bulbs must implement mqtt_topics")
