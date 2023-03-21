import pytest

from ..light import pick_light

def test_mytest():
    assert pick_light({}) is None
