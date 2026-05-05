from types import SimpleNamespace

from src.main import _channel_key


def test_channel_key_uses_username_when_present():
    chat = SimpleNamespace(username="durov", id=12345)
    assert _channel_key(chat) == "durov"


def test_channel_key_falls_back_to_id_when_no_username():
    chat = SimpleNamespace(username=None, id=12345)
    assert _channel_key(chat) == "12345"


def test_channel_key_handles_missing_username_attr():
    chat = SimpleNamespace(id=999)
    assert _channel_key(chat) == "999"
