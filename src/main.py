import asyncio
import logging
from pathlib import Path

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from src.config import Config, load_config
from src.state import State


logger = logging.getLogger("mirror")
DB_PATH = Path("data/state.db")


def _channel_key(chat) -> str:
    """Stable identifier used as state key. Prefer username for public channels."""
    username = getattr(chat, "username", None)
    return username if username else str(chat.id)


async def _setup_channel(client: TelegramClient, username: str, target, state: State):
    """Resolve channel, baseline if first run, backfill missed messages otherwise."""
    ent = await client.get_entity(username)
    last_seen = await state.get_last_seen_id(username)

    latest_id = 0
    async for msg in client.iter_messages(ent, limit=1):
        latest_id = msg.id
        break

    if last_seen is None:
        await state.set_last_seen_id(username, latest_id)
        logger.info("First run for %s: baseline=%d", username, latest_id)
        return ent

    if latest_id > last_seen:
        logger.info("Backfilling %s from %d to %d", username, last_seen, latest_id)
        messages = []
        async for msg in client.iter_messages(ent, min_id=last_seen):
            messages.append(msg)
        for msg in reversed(messages):
            try:
                await msg.forward_to(target)
                await state.set_last_seen_id(username, msg.id)
                logger.info("Backfilled %s/%d", username, msg.id)
            except Exception:
                logger.exception("Backfill forward failed for %s/%d", username, msg.id)

    return ent


async def run(config: Config) -> None:
    state = State(DB_PATH)
    await state.connect()

    client = TelegramClient(
        StringSession(config.session_string),
        config.api_id,
        config.api_hash,
    )

    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("SESSION_STRING is invalid or revoked; re-run login.py")

    me = await client.get_me()
    logger.info("Logged in as @%s (id=%s)", me.username or me.first_name, me.id)

    target = await client.get_entity(config.channel_id)
    logger.info("Target: %s (id=%s)", getattr(target, "title", "?"), config.channel_id)

    entities = []
    for username in config.channels:
        try:
            ent = await _setup_channel(client, username, target, state)
            entities.append(ent)
        except Exception:
            logger.exception("Failed to set up %s; skipping", username)

    if not entities:
        raise RuntimeError("No source channels could be resolved")

    @client.on(events.NewMessage(chats=entities))
    async def handler(event):
        chat = await event.get_chat()
        key = _channel_key(chat)
        try:
            await event.message.forward_to(target)
            await state.set_last_seen_id(key, event.message.id)
            logger.info("Forwarded %s/%d", key, event.message.id)
        except Exception:
            logger.exception("Forward failed for %s/%d", key, event.message.id)

    logger.info("Listening on %d channels...", len(entities))
    try:
        await client.run_until_disconnected()
    finally:
        await client.disconnect()
        await state.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    config = load_config()
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
