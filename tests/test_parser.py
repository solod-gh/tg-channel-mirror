from pathlib import Path

from src.parser import Post, parse_posts


FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_text_only_post():
    posts = parse_posts(load("post_text_only.html"))

    assert len(posts) == 1
    p = posts[0]
    assert p.channel == "durov"
    assert p.message_id == 123
    assert p.text_html == "Hello, <b>world</b>!"
    assert p.link == "https://t.me/durov/123"
    assert p.photos == []
    assert p.videos == []
    assert p.grouped_id is None


def test_parse_real_telegram_channel_returns_posts():
    posts = parse_posts(load("telegram_channel.html"))

    assert len(posts) > 0
    for p in posts:
        assert p.channel == "telegram"
        assert p.message_id > 0
        assert p.link.startswith("https://t.me/telegram/")


def test_parse_real_telegram_channel_posts_sorted_by_id():
    posts = parse_posts(load("telegram_channel.html"))
    ids = [p.message_id for p in posts]
    assert ids == sorted(ids), "posts should be returned in ascending id order"


def test_parse_post_with_photo():
    posts = parse_posts(load("post_with_photo.html"))
    assert len(posts) == 1
    p = posts[0]
    assert p.photos == ["https://cdn4.cdn-telegram.org/file/photo123.jpg"]
    assert p.videos == []
    assert p.text_html == "photo caption"


def test_parse_post_with_video():
    posts = parse_posts(load("post_with_video.html"))
    assert len(posts) == 1
    p = posts[0]
    assert p.videos == ["https://cdn4.cdn-telegram.org/file/video123.mp4"]
    assert p.photos == []


def test_parse_album():
    posts = parse_posts(load("post_album.html"))
    assert len(posts) == 1
    p = posts[0]
    assert p.grouped_id == "123456789"
    assert p.photos == [
        "https://cdn4.cdn-telegram.org/file/p1.jpg",
        "https://cdn4.cdn-telegram.org/file/p2.jpg",
    ]
