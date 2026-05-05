import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    channel_id: str
    channels: list[str]
    poll_interval: int
    dedup_window_hours: int


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN env var is required")

    channel_id = os.getenv("CHANNEL_ID", "").strip()
    if not channel_id:
        raise RuntimeError("CHANNEL_ID env var is required")

    channels_raw = os.getenv("CHANNELS", "").strip()
    channels = [c.strip().lstrip("@") for c in channels_raw.split(",") if c.strip()]
    if not channels:
        raise RuntimeError("CHANNELS env var must list at least one channel")

    poll_interval = int(os.getenv("POLL_INTERVAL", "60"))
    dedup_window_hours = int(os.getenv("DEDUP_WINDOW", "24"))

    return Config(
        bot_token=bot_token,
        channel_id=channel_id,
        channels=channels,
        poll_interval=poll_interval,
        dedup_window_hours=dedup_window_hours,
    )
