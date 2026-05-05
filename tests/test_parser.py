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
