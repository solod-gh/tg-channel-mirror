# TG Channel Mirror

Юзербот на Telethon. Подписан на список публичных TG-каналов через запасной user-аккаунт; на каждый новый пост делает нативный `forward_messages` в твой приватный канал — с пометкой «Forwarded from @channel» и всеми медиа без потерь.

## Один раз: получить SESSION_STRING

1. С запасного аккаунта зайти на https://my.telegram.org/apps, создать application, получить `API_ID` и `API_HASH`.
2. Локально:
   ```
   python3.12 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python login.py
   ```
   Скрипт спросит API_ID / API_HASH, затем номер запасного аккаунта и одноразовый код из TG. На выходе напечатает `SESSION_STRING`.
3. Запасной аккаунт должен быть подписан на каналы-источники и быть админом в целевом канале (с правом Post Messages).

## Локальный запуск

1. `cp .env.example .env`, заполнить значения.
2. `pip install -r requirements.txt -r requirements-dev.txt`
3. `python -m src.main`

## Тесты

`pytest`

## Деплой на Railway

1. Подключить репозиторий.
2. Variables: `API_ID`, `API_HASH`, `SESSION_STRING`, `CHANNEL_ID`, `CHANNELS`.
3. Settings → Start Command: `python -m src.main`.
4. (Опц.) Volume на `/app/data` — чтобы `state.db` пережил редеплой.
