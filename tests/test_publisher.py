from unittest.mock import AsyncMock, MagicMock

import pytest

from src.parser import Post
from src.publisher import Publisher


@pytest.fixture
def bot_mock():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


async def test_publish_sends_link(bot_mock):
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(Post(channel="durov", message_id=42))

    bot_mock.send_message.assert_awaited_once()
    kwargs = bot_mock.send_message.await_args.kwargs
    assert kwargs["chat_id"] == "-100123"
    assert kwargs["text"] == "https://t.me/durov/42"
    assert kwargs["disable_web_page_preview"] is False


async def test_publish_retries_on_rate_limit(bot_mock, monkeypatch):
    from aiogram.exceptions import TelegramRetryAfter
    from aiogram.methods import SendMessage

    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    bot_mock.send_message = AsyncMock(side_effect=[
        TelegramRetryAfter(
            method=SendMessage(chat_id=1, text="x"),
            message="Too Many Requests",
            retry_after=2,
        ),
        None,
    ])

    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(Post(channel="durov", message_id=1))

    assert bot_mock.send_message.await_count == 2
