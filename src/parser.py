from dataclasses import dataclass, field

from selectolax.parser import HTMLParser, Node


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
    text_html = text_node.html if text_node else ""
    if text_html:
        text_html = _strip_outer_div(text_html)

    date_link = node.css_first("a.tgme_widget_message_date")
    link = date_link.attributes.get("href", "") if date_link else ""

    return Post(
        channel=channel,
        message_id=message_id,
        text_html=text_html,
        link=link,
    )


def _strip_outer_div(html: str) -> str:
    """selectolax .html includes the outer tag; we want just inner content."""
    inner_start = html.find(">")
    inner_end = html.rfind("<")
    if inner_start == -1 or inner_end == -1 or inner_end <= inner_start:
        return html
    return html[inner_start + 1 : inner_end]
