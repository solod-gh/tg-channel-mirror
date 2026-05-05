from unittest.mock import AsyncMock, MagicMock

import pytest

from src.parser import Post
from src.publisher import Publisher, build_caption, split_long_text, MAX_TEXT


def make_post(**kwargs) -> Post:
    defaults = dict(
        channel="durov",
        message_id=1,
        text_html="hello",
        link="https://t.me/durov/1",
        photos=[],
        videos=[],
        grouped_id=None,
    )
    defaults.update(kwargs)
    return Post(**defaults)


def test_build_caption_appends_attribution():
    p = make_post(text_html="hello")
    caption = build_caption(p)
    assert "hello" in caption
    assert '<a href="https://t.me/durov/1">📡 @durov</a>' in caption


def test_build_caption_handles_empty_text():
    p = make_post(text_html="")
    caption = build_caption(p)
    assert caption.startswith('<a href="')
    assert "@durov" in caption


def test_split_long_text_under_limit_returns_single_chunk():
    text = "short text"
    assert split_long_text(text) == ["short text"]


def test_split_long_text_splits_on_paragraph_boundary():
    para_a = "A" * 2000
    para_b = "B" * 2000
    para_c = "C" * 2000
    text = f"{para_a}\n\n{para_b}\n\n{para_c}"
    chunks = split_long_text(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= MAX_TEXT


def test_split_long_text_hard_splits_when_no_paragraphs():
    text = "X" * (MAX_TEXT + 100)
    chunks = split_long_text(text)
    assert len(chunks) == 2
    assert "".join(chunks) == text


def test_split_long_text_strips_empty_leading_chunk():
    text = "\n\n" + "X" * (MAX_TEXT + 100)
    chunks = split_long_text(text)
    for c in chunks:
        assert c, "no chunk should be empty"
    assert len(chunks) == 2


@pytest.fixture
def bot_mock():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_video = AsyncMock()
    bot.send_media_group = AsyncMock()
    return bot


async def test_publish_text_only_post(bot_mock):
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(text_html="just text"))

    bot_mock.send_message.assert_awaited_once()
    kwargs = bot_mock.send_message.await_args.kwargs
    assert kwargs["chat_id"] == "-100123"
    assert "just text" in kwargs["text"]
    assert "@durov" in kwargs["text"]


async def test_publish_single_photo_uses_send_photo(bot_mock):
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(
        text_html="cap",
        photos=["https://cdn/p.jpg"],
    ))

    bot_mock.send_photo.assert_awaited_once()
    bot_mock.send_message.assert_not_awaited()
    kwargs = bot_mock.send_photo.await_args.kwargs
    assert kwargs["photo"] == "https://cdn/p.jpg"
    assert "cap" in kwargs["caption"]


async def test_publish_single_video_uses_send_video(bot_mock):
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(
        text_html="cap",
        videos=["https://cdn/v.mp4"],
    ))

    bot_mock.send_video.assert_awaited_once()


async def test_publish_album_uses_send_media_group(bot_mock):
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(
        text_html="album",
        photos=["https://cdn/p1.jpg", "https://cdn/p2.jpg"],
        grouped_id="555",
    ))

    bot_mock.send_media_group.assert_awaited_once()
    bot_mock.send_photo.assert_not_awaited()
    media = bot_mock.send_media_group.await_args.kwargs["media"]
    assert len(media) == 2


async def test_publish_long_text_sends_multiple_messages(bot_mock):
    long_text = ("X" * 5000)
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(text_html=long_text))

    assert bot_mock.send_message.await_count >= 2
