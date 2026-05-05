import html
import re
from dataclasses import dataclass, field

from selectolax.parser import HTMLParser, Node


_BG_URL_RE = re.compile(r"background-image\s*:\s*url\(['\"]?([^'\")]+)['\"]?\)")

_ALLOWED_TAGS = frozenset({
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "a", "code", "pre", "blockquote", "tg-spoiler",
})


@dataclass(frozen=True)
class Post:
    channel: str
    message_id: int
    text_html: str
    link: str
    photos: list[str] = field(default_factory=list)
    videos: list[str] = field(default_factory=list)
    grouped_id: str | None = None


def parse_posts(html: str) -> list[Post]:
    tree = HTMLParser(html)
    nodes = tree.css("div.tgme_widget_message[data-post]")
    posts = [_parse_one(n) for n in nodes]
    posts = [p for p in posts if p is not None]
    posts.sort(key=lambda p: p.message_id)
    return posts


def _parse_one(node: Node) -> Post | None:
    data_post = node.attributes.get("data-post", "")
    if "/" not in data_post:
        return None
    channel, id_str = data_post.split("/", 1)
    try:
        message_id = int(id_str)
    except ValueError:
        return None

    text_node = node.css_first("div.tgme_widget_message_text")
    text_html = _sanitize_to_telegram_html(text_node) if text_node else ""

    date_link = node.css_first("a.tgme_widget_message_date")
    link = date_link.attributes.get("href", "") if date_link else ""

    photos: list[str] = []
    for photo_node in node.css("a.tgme_widget_message_photo_wrap"):
        style = photo_node.attributes.get("style", "")
        m = _BG_URL_RE.search(style)
        if m:
            photos.append(m.group(1))

    videos: list[str] = []
    for video_node in node.css("video.tgme_widget_message_video, video.tgme_widget_message_roundvideo"):
        src = video_node.attributes.get("src", "")
        if src:
            videos.append(src)

    grouped_id: str | None = None
    grouped_wrap = node.css_first("div.tgme_widget_message_grouped_wrap")
    if grouped_wrap:
        grouped_id = grouped_wrap.attributes.get("data-grouped-id")

    return Post(
        channel=channel,
        message_id=message_id,
        text_html=text_html,
        link=link,
        photos=photos,
        videos=videos,
        grouped_id=grouped_id,
    )


def _sanitize_to_telegram_html(node: Node) -> str:
    """Walk a selectolax node's children, emit Telegram-compatible HTML.
    Only the children are walked — the node itself is treated as a wrapper."""
    parts: list[str] = []
    for child in node.iter(include_text=True):
        tag = child.tag
        if tag == "-text":
            parts.append(html.escape(child.text(deep=False) or "", quote=False))
        elif tag == "br":
            parts.append("\n")
        elif tag in ("div", "p"):
            inner = _sanitize_to_telegram_html(child)
            parts.append(inner)
            if inner and not inner.endswith("\n"):
                parts.append("\n")
        elif tag == "a":
            inner = _sanitize_to_telegram_html(child)
            href = html.escape(child.attributes.get("href", "") or "", quote=True)
            parts.append(f'<a href="{href}">{inner}</a>')
        elif tag in _ALLOWED_TAGS:
            inner = _sanitize_to_telegram_html(child)
            parts.append(f"<{tag}>{inner}</{tag}>")
        else:
            parts.append(_sanitize_to_telegram_html(child))
    return "".join(parts).strip("\n")
