import textwrap
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


def _make_post_html(inner: str, post_id: int = 999) -> str:
    return textwrap.dedent(f'''
        <div class="tgme_widget_message" data-post="x/{post_id}">
          <a class="tgme_widget_message_date" href="https://t.me/x/{post_id}"></a>
          <div class="tgme_widget_message_text">{inner}</div>
        </div>
    ''')


def test_sanitize_drops_nested_div():
    posts = parse_posts(_make_post_html(
        '<div class="tgme_widget_message_text">Как делишки?</div>'
    ))
    assert posts[0].text_html == "Как делишки?"


def test_sanitize_keeps_allowed_formatting():
    posts = parse_posts(_make_post_html(
        '<b>bold</b> <i>italic</i> <a href="https://x.com">link</a>'
    ))
    assert posts[0].text_html == '<b>bold</b> <i>italic</i> <a href="https://x.com">link</a>'


def test_sanitize_converts_br_to_newline():
    posts = parse_posts(_make_post_html('line1<br/>line2<br>line3'))
    assert posts[0].text_html == "line1\nline2\nline3"


def test_sanitize_escapes_text_special_chars():
    posts = parse_posts(_make_post_html('a &amp; b &lt; c &gt; d'))
    assert posts[0].text_html == "a &amp; b &lt; c &gt; d"


def test_sanitize_drops_unknown_tags_keeps_content():
    posts = parse_posts(_make_post_html('<span class="x"><b>kept</b></span>'))
    assert posts[0].text_html == "<b>kept</b>"


def test_sanitize_escapes_href_attribute():
    posts = parse_posts(_make_post_html(
        '<a href="https://x.com/?q=1&amp;r=2">link</a>'
    ))
    assert '<a href="https://x.com/?q=1&amp;r=2">link</a>' in posts[0].text_html


def test_parse_round_video():
    posts = parse_posts(load("post_with_roundvideo.html"))
    assert len(posts) == 1
    p = posts[0]
    assert p.videos == ["https://cdn4.telesco.pe/file/round1.mp4?token=abc"]
    assert p.photos == []
