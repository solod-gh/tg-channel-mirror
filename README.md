# TG Channel Mirror

Зеркалит посты из публичных Telegram-каналов в твой приватный канал.

## Локальный запуск

1. `python3.12 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt -r requirements-dev.txt`
3. `cp .env.example .env`, заполнить.
4. `python -m src.main`

## Тесты

`pytest`

## Деплой на Railway

1. Подключить этот репозиторий в Railway.
2. Project Settings → Variables: добавить `BOT_TOKEN`, `CHANNEL_ID`, `CHANNELS`.
3. Деплой автоматический.
