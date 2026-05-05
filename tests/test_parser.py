from pathlib import Path

from src.parser import Post, parse_posts


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_extracts_channel_and_id():
    html = '<div class="tgme_widget_message" data-post="durov/123"></div>'
    posts = parse_posts(html)
    assert posts == [Post(channel="durov", message_id=123)]


def test_post_link_property():
    p = Post(channel="durov", message_id=42)
    assert p.link == "https://t.me/durov/42"


def test_parse_skips_malformed_data_post():
    html = (
        '<div class="tgme_widget_message" data-post="bad"></div>'
        '<div class="tgme_widget_message" data-post="durov/notanint"></div>'
        '<div class="tgme_widget_message" data-post="ok/7"></div>'
    )
    posts = parse_posts(html)
    assert posts == [Post(channel="ok", message_id=7)]


def test_parse_sorts_by_id():
    html = (
        '<div class="tgme_widget_message" data-post="a/3"></div>'
        '<div class="tgme_widget_message" data-post="a/1"></div>'
        '<div class="tgme_widget_message" data-post="a/2"></div>'
    )
    posts = parse_posts(html)
    assert [p.message_id for p in posts] == [1, 2, 3]


def test_parse_real_telegram_fixture_returns_posts():
    fixture = FIXTURES / "telegram_channel.html"
    if not fixture.exists():
        return
    posts = parse_posts(fixture.read_text(encoding="utf-8"))
    assert len(posts) > 0
    for p in posts:
        assert p.channel == "telegram"
        assert p.message_id > 0
