import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter

from src.parser import Post


logger = logging.getLogger("publisher")


class Publisher:
    """Sends a t.me link for each new post; Telegram auto-previews it."""

    def __init__(self, bot: Bot, chat_id: str):
        self._bot = bot
        self._chat_id = chat_id

    async def publish(self, post: Post) -> None:
        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=post.link,
                disable_web_page_preview=False,
            )
        except TelegramRetryAfter as e:
            logger.warning("Rate-limited; sleeping %ss then retrying", e.retry_after)
            await asyncio.sleep(e.retry_after)
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=post.link,
                disable_web_page_preview=False,
            )
