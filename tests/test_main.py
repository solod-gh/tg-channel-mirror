from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.main import process_channel
from src.parser import Post
from src.state import State


def make_post(channel="durov", message_id=1, text="hi") -> Post:
    return Post(
        channel=channel,
        message_id=message_id,
        text_html=text,
        link=f"https://t.me/{channel}/{message_id}",
        photos=[],
        videos=[],
        grouped_id=None,
    )


@pytest.fixture
async def state(tmp_path: Path):
    s = State(tmp_path / "test.db")
    await s.connect()
    yield s
    await s.close()


async def test_first_run_sets_baseline_without_publishing(state: State):
    fetched = [make_post(message_id=10), make_post(message_id=11), make_post(message_id=12)]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    published_count = await process_channel(
        channel="durov",
        fetcher=fetcher,
        publisher=publisher,
        state=state,
        dedup_window_hours=24,
        now=datetime.now(timezone.utc),
    )

    assert published_count == 0
    publisher.publish.assert_not_awaited()
    assert await state.get_last_seen_id("durov") == 12


async def test_subsequent_run_publishes_only_new_posts(state: State):
    await state.set_last_seen_id("durov", 10)

    fetched = [make_post(message_id=10, text="old"), make_post(message_id=11, text="new1"), make_post(message_id=12, text="new2")]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    published_count = await process_channel(
        channel="durov",
        fetcher=fetcher,
        publisher=publisher,
        state=state,
        dedup_window_hours=24,
        now=datetime.now(timezone.utc),
    )

    assert published_count == 2
    assert publisher.publish.await_count == 2
    published_ids = [
        call.args[0].message_id for call in publisher.publish.await_args_list
    ]
    assert published_ids == [11, 12]
    assert await state.get_last_seen_id("durov") == 12


async def test_dedup_skips_post_with_same_text_from_another_channel(state: State):
    now = datetime.now(timezone.utc)
    await state.set_last_seen_id("durov", 10)
    await state.set_last_seen_id("other", 100)

    from src.main import _hash_text
    duplicate_text = "exact same body"
    await state.record_hash(_hash_text(duplicate_text), "other", now)

    fetched = [make_post(channel="durov", message_id=11, text=duplicate_text)]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    published_count = await process_channel(
        channel="durov",
        fetcher=fetcher,
        publisher=publisher,
        state=state,
        dedup_window_hours=24,
        now=now,
    )

    assert published_count == 0
    publisher.publish.assert_not_awaited()
    assert await state.get_last_seen_id("durov") == 11


async def test_fetcher_failure_does_not_advance_state(state: State):
    await state.set_last_seen_id("durov", 10)

    fetcher = AsyncMock(side_effect=RuntimeError("network down"))
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    with pytest.raises(RuntimeError):
        await process_channel(
            channel="durov",
            fetcher=fetcher,
            publisher=publisher,
            state=state,
            dedup_window_hours=24,
            now=datetime.now(timezone.utc),
        )

    assert await state.get_last_seen_id("durov") == 10


async def test_publish_failure_does_not_record_hash(state: State):
    await state.set_last_seen_id("durov", 10)

    fetched = [make_post(message_id=11, text="some text")]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock(side_effect=RuntimeError("publish boom"))

    now = datetime.now(timezone.utc)
    with pytest.raises(RuntimeError):
        await process_channel(
            channel="durov",
            fetcher=fetcher,
            publisher=publisher,
            state=state,
            dedup_window_hours=24,
            now=now,
        )

    from src.main import _hash_text
    assert await state.was_seen_recently(_hash_text("some text"), 24, now) is False
    assert await state.get_last_seen_id("durov") == 10


async def test_telegram_bad_request_advances_state_and_continues(state: State):
    from aiogram.exceptions import TelegramBadRequest
    from aiogram.methods import SendMessage

    await state.set_last_seen_id("durov", 10)

    fetched = [
        make_post(message_id=11, text="bad"),
        make_post(message_id=12, text="good"),
    ]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock(side_effect=[
        TelegramBadRequest(method=SendMessage(chat_id=1, text="x"), message="parse error"),
        None,
    ])

    published = await process_channel(
        channel="durov",
        fetcher=fetcher,
        publisher=publisher,
        state=state,
        dedup_window_hours=24,
        now=datetime.now(timezone.utc),
    )

    assert published == 1
    assert publisher.publish.await_count == 2
    assert await state.get_last_seen_id("durov") == 12
