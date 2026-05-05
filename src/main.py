import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

import httpx
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from src.config import Config, load_config
from src.parser import Post, parse_posts
from src.publisher import Publisher
from src.state import State


logger = logging.getLogger("mirror")

DB_PATH = Path("data/state.db")
HASH_PREFIX_LEN = 200


PostFetcher = Callable[[], Awaitable[list[Post]]]


def _hash_text(text: str) -> str:
    snippet = text.strip()[:HASH_PREFIX_LEN]
    return hashlib.sha256(snippet.encode("utf-8")).hexdigest()


async def fetch_channel_html(client: httpx.AsyncClient, channel: str) -> str:
    response = await client.get(f"https://t.me/s/{channel}", timeout=30.0)
    response.raise_for_status()
    return response.text


def make_fetcher(client: httpx.AsyncClient, channel: str) -> PostFetcher:
    async def _fetch() -> list[Post]:
        html = await fetch_channel_html(client, channel)
        return parse_posts(html)
    return _fetch


async def process_channel(
    channel: str,
    fetcher: PostFetcher,
    publisher: Publisher,
    state: State,
    dedup_window_hours: int,
    now: datetime,
) -> int:
    posts = await fetcher()
    if not posts:
        return 0

    last_seen = await state.get_last_seen_id(channel)
    is_first_run = last_seen is None
    max_id_in_batch = max(p.message_id for p in posts)

    if is_first_run:
        await state.set_last_seen_id(channel, max_id_in_batch)
        logger.info("First run for %s: baseline set to %d", channel, max_id_in_batch)
        return 0

    new_posts = [p for p in posts if p.message_id > last_seen]
    new_posts.sort(key=lambda p: p.message_id)

    published = 0
    for post in new_posts:
        text_for_hash = post.text_html or ""
        hash_ = _hash_text(text_for_hash) if text_for_hash else None

        if hash_ and await state.was_seen_recently(hash_, dedup_window_hours, now):
            logger.info("Dedup skip: %s/%d", channel, post.message_id)
            await state.set_last_seen_id(channel, post.message_id)
            continue

        try:
            await publisher.publish(post)
        except TelegramBadRequest:
            logger.exception(
                "Bad post %s/%d (Telegram rejected); skipping permanently",
                channel, post.message_id,
            )
            await state.set_last_seen_id(channel, post.message_id)
            continue
        except Exception:
            logger.exception("Failed to publish %s/%d", channel, post.message_id)
            raise

        if hash_:
            await state.record_hash(hash_, channel, now)
        await state.set_last_seen_id(channel, post.message_id)
        published += 1

    return published


async def cleanup_loop(state: State, window_hours: int, interval_seconds: int = 3600) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            now = datetime.now(timezone.utc)
            deleted = await state.cleanup_old_hashes(window_hours, now)
            if deleted:
                logger.info("Cleanup: removed %d old hashes", deleted)
        except Exception:
            logger.exception("Cleanup task failed")


async def run(config: Config) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    state = State(DB_PATH)
    await state.connect()

    bot = Bot(token=config.bot_token)
    publisher = Publisher(bot=bot, chat_id=config.channel_id)

    cleanup = asyncio.create_task(
        cleanup_loop(state, config.dedup_window_hours)
    )

    try:
        async with httpx.AsyncClient() as client:
            while True:
                cycle_start = datetime.now(timezone.utc)
                for channel in config.channels:
                    try:
                        await process_channel(
                            channel=channel,
                            fetcher=make_fetcher(client, channel),
                            publisher=publisher,
                            state=state,
                            dedup_window_hours=config.dedup_window_hours,
                            now=datetime.now(timezone.utc),
                        )
                    except Exception:
                        logger.exception("Channel %s failed; continuing", channel)
                elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
                sleep_for = max(0.0, config.poll_interval - elapsed)
                await asyncio.sleep(sleep_for)
    finally:
        cleanup.cancel()
        await bot.session.close()
        await state.close()


def main() -> None:
    config = load_config()
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
