import asyncio
import logging
from typing import Any

import httpx
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import BufferedInputFile, InputMediaPhoto, InputMediaVideo

from src.parser import Post

logger = logging.getLogger("publisher")


MAX_TEXT = 4096
MAX_CAPTION = 1024
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50 MB Bot API upload limit
DOWNLOAD_TIMEOUT_SECONDS = 60.0


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
    def __init__(
        self,
        bot: Bot,
        chat_id: str,
        http_client: httpx.AsyncClient,
    ):
        self._bot = bot
        self._chat_id = chat_id
        self._http = http_client

    async def _download(self, url: str, fallback_name: str) -> BufferedInputFile | None:
        """Download media bytes. Returns None if download fails or exceeds size limit."""
        try:
            response = await self._http.get(url, timeout=DOWNLOAD_TIMEOUT_SECONDS)
            response.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.warning("Failed to download %s: %s", url, e)
            return None
        if len(response.content) > MAX_DOWNLOAD_BYTES:
            logger.warning(
                "Skipping oversize media %s (%d bytes > %d)",
                url, len(response.content), MAX_DOWNLOAD_BYTES,
            )
            return None
        # Filename: take last URL path segment, strip query string. Fallback if empty.
        name = url.rsplit("/", 1)[-1].split("?")[0] or fallback_name
        return BufferedInputFile(response.content, filename=name)

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
        photo_file = await self._download(post.photos[0], "photo.jpg")
        if photo_file is None:
            await self._send_text(post)  # fallback: text-only
            return
        caption = build_caption(post)
        if len(caption) > MAX_CAPTION:
            await self._call(self._bot.send_photo, chat_id=self._chat_id, photo=photo_file)
            for chunk in split_long_text(caption):
                await self._call(
                    self._bot.send_message,
                    chat_id=self._chat_id, text=chunk, parse_mode="HTML",
                )
        else:
            await self._call(
                self._bot.send_photo,
                chat_id=self._chat_id, photo=photo_file,
                caption=caption, parse_mode="HTML",
            )

    async def _send_video(self, post: Post) -> None:
        video_file = await self._download(post.videos[0], "video.mp4")
        if video_file is None:
            await self._send_text(post)  # fallback: text-only
            return
        caption = build_caption(post)
        if len(caption) > MAX_CAPTION:
            await self._call(self._bot.send_video, chat_id=self._chat_id, video=video_file)
            for chunk in split_long_text(caption):
                await self._call(
                    self._bot.send_message,
                    chat_id=self._chat_id, text=chunk, parse_mode="HTML",
                )
        else:
            await self._call(
                self._bot.send_video,
                chat_id=self._chat_id, video=video_file,
                caption=caption, parse_mode="HTML",
            )

    async def _send_album(self, post: Post) -> None:
        downloaded: list[tuple[str, BufferedInputFile]] = []
        for url in post.photos:
            f = await self._download(url, "photo.jpg")
            if f is None:
                await self._send_text(post)
                return
            downloaded.append(("photo", f))
        for url in post.videos:
            f = await self._download(url, "video.mp4")
            if f is None:
                await self._send_text(post)
                return
            downloaded.append(("video", f))

        caption = build_caption(post)
        media: list[Any] = []
        for i, (kind, f) in enumerate(downloaded):
            cap = caption if i == 0 and len(caption) <= MAX_CAPTION else None
            parse_mode = "HTML" if cap else None
            if kind == "photo":
                media.append(InputMediaPhoto(media=f, caption=cap, parse_mode=parse_mode))
            else:
                media.append(InputMediaVideo(media=f, caption=cap, parse_mode=parse_mode))

        await self._call(self._bot.send_media_group, chat_id=self._chat_id, media=media)
        if len(caption) > MAX_CAPTION:
            for chunk in split_long_text(caption):
                await self._call(
                    self._bot.send_message,
                    chat_id=self._chat_id, text=chunk, parse_mode="HTML",
                )
