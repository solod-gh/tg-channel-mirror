import pytest

from src.config import load_config


def _set_required(monkeypatch):
    monkeypatch.setattr("src.config.load_dotenv", lambda *a, **kw: False)
    monkeypatch.setenv("API_ID", "12345678")
    monkeypatch.setenv("API_HASH", "abc123")
    monkeypatch.setenv("SESSION_STRING", "fake-session")
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", "durov,telegram")


def test_load_config_returns_dataclass(monkeypatch):
    _set_required(monkeypatch)

    cfg = load_config()

    assert cfg.api_id == 12345678
    assert cfg.api_hash == "abc123"
    assert cfg.session_string == "fake-session"
    assert cfg.channel_id == -1001234567890
    assert cfg.channels == ["durov", "telegram"]


def test_load_config_strips_whitespace_and_at_signs(monkeypatch):
    _set_required(monkeypatch)
    monkeypatch.setenv("CHANNELS", " @durov , telegram , ")

    cfg = load_config()
    assert cfg.channels == ["durov", "telegram"]


def test_load_config_raises_on_missing_required(monkeypatch):
    _set_required(monkeypatch)
    monkeypatch.delenv("API_ID")

    with pytest.raises(RuntimeError, match="API_ID"):
        load_config()


def test_load_config_raises_on_missing_session(monkeypatch):
    _set_required(monkeypatch)
    monkeypatch.delenv("SESSION_STRING")

    with pytest.raises(RuntimeError, match="SESSION_STRING"):
        load_config()


def test_load_config_raises_on_empty_channels(monkeypatch):
    _set_required(monkeypatch)
    monkeypatch.setenv("CHANNELS", "")

    with pytest.raises(RuntimeError, match="CHANNELS"):
        load_config()
