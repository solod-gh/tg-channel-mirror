"""One-time interactive login for Telethon. Generates SESSION_STRING for env var.

Запускается локально один раз:
    python login.py

Введёт credentials с https://my.telegram.org/apps, затем номер запасного
аккаунта, затем код подтверждения из TG. На выходе печатает SESSION_STRING,
который нужно положить в Railway env vars.
"""
import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main() -> None:
    print("Введи credentials с https://my.telegram.org/apps")
    api_id = int(input("API_ID: ").strip())
    api_hash = input("API_HASH: ").strip()

    print("\nЗалогинюсь под запасным аккаунтом.")
    print("В TG-чат от Telegram придёт код — введи когда попросит.\n")

    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        me = await client.get_me()
        username = f"@{me.username}" if me.username else me.first_name
        print(f"\nГотово. Залогинен как: {username} (id={me.id})\n")

        sep = "=" * 60
        print(sep)
        print("SESSION_STRING (скопируй в Railway env var):")
        print(client.session.save())
        print(sep)
        print("\nДобавь в Railway → Variables:")
        print(f"  API_ID={api_id}")
        print(f"  API_HASH={api_hash}")
        print("  SESSION_STRING=<строка выше>")
        print("  CHANNEL_ID=-1003994292004  (твой канал, остаётся)")
        print("  CHANNELS=...                (источники, остаётся)")
        print("\nПосле этого можно убрать BOT_TOKEN — он больше не нужен.")


if __name__ == "__main__":
    asyncio.run(main())
