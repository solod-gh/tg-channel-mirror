import asyncio
import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InputMediaPhoto, InputMediaVideo

from src.parser import Post

logger = logging.getLogger("publisher")


MAX_TEXT = 4096
MAX_CAPTION = 1024


def build_caption(post: Post) -> str:
    attribution = f'<a href="{post.link}">📡 @{post.channel}</a>'
    if post.text_html:
        return f"{post.text_html}\n\n{attribution}"
    return attribution


def split_long_text(text: str, limit: int = MAX_TEXT) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        cut = remaining.rfind("\n\n", 0, limit)
        if cut == -1:
            cut = remaining.rfind("\n", 0, limit)
        if cut == -1:
            cut = limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return [c for c in chunks if c]


class Publisher:
    def __init__(self, bot: Bot, chat_id: str):
        self._bot = bot
        self._chat_id = chat_id

    async def _call(self, method, **kwargs):
        try:
            return await method(**kwargs)
        except TelegramRetryAfter as e:
            logger.warning("Rate-limited; sleeping %ss then retrying", e.retry_after)
            await asyncio.sleep(e.retry_after)
            return await method(**kwargs)

    async def publish(self, post: Post) -> None:
        if post.photos and post.grouped_id:
            await self._send_album(post)
            return

        if len(post.photos) == 1 and not post.videos:
            await self._send_photo(post)
            return

        if len(post.videos) == 1 and not post.photos:
            await self._send_video(post)
            return

        await self._send_text(post)

    async def _send_text(self, post: Post) -> None:
        full = build_caption(post)
        for chunk in split_long_text(full):
            await self._call(
                self._bot.send_message,
                chat_id=self._chat_id,
                text=chunk,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )

    async def _send_photo(self, post: Post) -> None:
        caption = build_caption(post)
        if len(caption) > MAX_CAPTION:
            await self._call(
                self._bot.send_photo,
                chat_id=self._chat_id,
                photo=post.photos[0],
            )
            for chunk in split_long_text(caption):
                await self._call(
                    self._bot.send_message,
                    chat_id=self._chat_id,
                    text=chunk,
                    parse_mode="HTML",
                )
        else:
            await self._call(
                self._bot.send_photo,
                chat_id=self._chat_id,
                photo=post.photos[0],
                caption=caption,
                parse_mode="HTML",
            )

    async def _send_video(self, post: Post) -> None:
        caption = build_caption(post)
        if len(caption) > MAX_CAPTION:
            await self._call(
                self._bot.send_video,
                chat_id=self._chat_id,
                video=post.videos[0],
            )
            for chunk in split_long_text(caption):
                await self._call(
                    self._bot.send_message,
                    chat_id=self._chat_id,
                    text=chunk,
                    parse_mode="HTML",
                )
        else:
            await self._call(
                self._bot.send_video,
                chat_id=self._chat_id,
                video=post.videos[0],
                caption=caption,
                parse_mode="HTML",
            )

    async def _send_album(self, post: Post) -> None:
        caption = build_caption(post)
        media: list[Any] = []
        for i, url in enumerate(post.photos):
            media.append(InputMediaPhoto(
                media=url,
                caption=caption if i == 0 and len(caption) <= MAX_CAPTION else None,
                parse_mode="HTML" if i == 0 else None,
            ))
        for i, url in enumerate(post.videos):
            media.append(InputMediaVideo(media=url))

        await self._call(
            self._bot.send_media_group,
            chat_id=self._chat_id,
            media=media,
        )
        if len(caption) > MAX_CAPTION:
            for chunk in split_long_text(caption):
                await self._call(
                    self._bot.send_message,
                    chat_id=self._chat_id,
                    text=chunk,
                    parse_mode="HTML",
                )
