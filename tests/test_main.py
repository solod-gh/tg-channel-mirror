from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.main import process_channel
from src.parser import Post
from src.state import State


def _post(channel="durov", message_id=1) -> Post:
    return Post(channel=channel, message_id=message_id)


@pytest.fixture
async def state(tmp_path: Path):
    s = State(tmp_path / "test.db")
    await s.connect()
    yield s
    await s.close()


async def test_first_run_sets_baseline_without_publishing(state: State):
    fetched = [_post(message_id=10), _post(message_id=11), _post(message_id=12)]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    published = await process_channel(
        channel="durov", fetcher=fetcher, publisher=publisher, state=state,
    )

    assert published == 0
    publisher.publish.assert_not_awaited()
    assert await state.get_last_seen_id("durov") == 12


async def test_subsequent_run_publishes_only_new_posts(state: State):
    await state.set_last_seen_id("durov", 10)
    fetched = [_post(message_id=10), _post(message_id=11), _post(message_id=12)]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    published = await process_channel(
        channel="durov", fetcher=fetcher, publisher=publisher, state=state,
    )

    assert published == 2
    assert publisher.publish.await_count == 2
    published_ids = [
        c.args[0].message_id for c in publisher.publish.await_args_list
    ]
    assert published_ids == [11, 12]
    assert await state.get_last_seen_id("durov") == 12


async def test_fetcher_failure_does_not_advance_state(state: State):
    await state.set_last_seen_id("durov", 10)
    fetcher = AsyncMock(side_effect=RuntimeError("boom"))
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    with pytest.raises(RuntimeError):
        await process_channel(
            channel="durov", fetcher=fetcher, publisher=publisher, state=state,
        )

    assert await state.get_last_seen_id("durov") == 10


async def test_telegram_bad_request_advances_state_and_continues(state: State):
    from aiogram.exceptions import TelegramBadRequest
    from aiogram.methods import SendMessage

    await state.set_last_seen_id("durov", 10)
    fetched = [_post(message_id=11), _post(message_id=12)]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock(side_effect=[
        TelegramBadRequest(method=SendMessage(chat_id=1, text="x"), message="parse error"),
        None,
    ])

    published = await process_channel(
        channel="durov", fetcher=fetcher, publisher=publisher, state=state,
    )

    assert published == 1
    assert publisher.publish.await_count == 2
    assert await state.get_last_seen_id("durov") == 12
