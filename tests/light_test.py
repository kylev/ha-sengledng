import pytest

from .. import light

from .fixtures import bulbs


def test_pick_light_default():
    assert light.pick_light({}) is None


def test_pick_light_color_wifi():
    assert light.pick_light(bulbs.BULB_W21N13) is light.ElementsColorLightEntity


def test_pick_light_white_wifi():
    assert light.pick_light(bulbs.BULB_W21N11) is light.ElementsLightEntity
