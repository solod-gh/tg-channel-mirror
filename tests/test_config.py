import pytest
from src.config import Config, load_config


def test_load_config_returns_dataclass(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", "durov,telegram")
    monkeypatch.delenv("POLL_INTERVAL", raising=False)

    cfg = load_config()

    assert cfg.bot_token == "abc"
    assert cfg.channel_id == "-1001234567890"
    assert cfg.channels == ["durov", "telegram"]
    assert cfg.poll_interval == 60


def test_load_config_strips_whitespace_and_at_signs(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", " @durov , telegram , ")

    cfg = load_config()

    assert cfg.channels == ["durov", "telegram"]


def test_load_config_uses_overrides(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", "durov")
    monkeypatch.setenv("POLL_INTERVAL", "30")

    cfg = load_config()

    assert cfg.poll_interval == 30


def test_load_config_raises_on_missing_required(monkeypatch):
    monkeypatch.setattr("src.config.load_dotenv", lambda *a, **kw: False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", "durov")

    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        load_config()


def test_load_config_raises_on_empty_channels(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", "")

    with pytest.raises(RuntimeError, match="CHANNELS"):
        load_config()
