from dataclasses import dataclass

from selectolax.parser import HTMLParser


@dataclass(frozen=True)
class Post:
    channel: str
    message_id: int

    @property
    def link(self) -> str:
        return f"https://t.me/{self.channel}/{self.message_id}"


def parse_posts(html: str) -> list[Post]:
    tree = HTMLParser(html)
    posts: list[Post] = []
    for node in tree.css("div.tgme_widget_message[data-post]"):
        data_post = node.attributes.get("data-post", "")
        if "/" not in data_post:
            continue
        channel, id_str = data_post.split("/", 1)
        try:
            message_id = int(id_str)
        except ValueError:
            continue
        posts.append(Post(channel=channel, message_id=message_id))
    posts.sort(key=lambda p: p.message_id)
    return posts
