import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    session_string: str
    channel_id: int
    channels: list[str]


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} env var is required")
    return value


def load_config() -> Config:
    load_dotenv()

    api_id = int(_required("API_ID"))
    api_hash = _required("API_HASH")
    session_string = _required("SESSION_STRING")
    channel_id = int(_required("CHANNEL_ID"))

    channels_raw = _required("CHANNELS")
    channels = [c.strip().lstrip("@") for c in channels_raw.split(",") if c.strip()]
    if not channels:
        raise RuntimeError("CHANNELS env var must list at least one channel")

    return Config(
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string,
        channel_id=channel_id,
        channels=channels,
    )
