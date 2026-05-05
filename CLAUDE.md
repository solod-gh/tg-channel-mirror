# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A long-running Python worker that mirrors posts from public Telegram channels into one private "feed" channel. It polls each source channel's public web view (`https://t.me/s/<channel>`), detects new `message_id`s, and posts a `https://t.me/<channel>/<id>` link into the target channel. Telegram's native link-preview renders each link as a card with media + start of text, so the feed reads like a forwarded-from view despite being plain `sendMessage` calls.

## Commands

Setup (Python 3.12 expected):
```
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env  # fill BOT_TOKEN, CHANNEL_ID, CHANNELS
```

Run locally: `python -m src.main`

Tests: `pytest` (full suite). Single test: `pytest tests/test_main.py::test_subsequent_run_publishes_only_new_posts -v`

Deployment: Railway auto-deploys on push to `main`. Procfile runs `python -m src.main` as a `worker` process. Env vars set in Railway → Variables.

## Architecture

Five modules, each with one responsibility:

- **`src/parser.py`** — pure HTML → `list[Post(channel, message_id)]`. Reads `data-post="channel/id"` attributes from `t.me/s/` HTML. The `Post` dataclass is intentionally tiny — only the fields needed to build a `t.me` URL.
- **`src/publisher.py`** — wraps `aiogram.Bot.send_message`, sends `post.link` with link previews enabled. Retries once on `TelegramRetryAfter`.
- **`src/state.py`** — single-table SQLite (`channel_state`) for `last_seen_id` per channel. The only persistence; lost state on restart just means re-baselining (no spam, see below).
- **`src/main.py`** — orchestrator. Polls each channel every `POLL_INTERVAL` seconds, dispatches new posts (id > last_seen) to the publisher, advances state on success.
- **`src/config.py`** — env var loader with explicit validation, returns a frozen `Config` dataclass.

Two important behaviors that aren't obvious from individual files:

**First-run baselining.** When a channel has no `last_seen_id` in SQLite, `process_channel` records the current max id and publishes nothing. This prevents backfilling the entire history of every source channel on first deploy or after a state reset.

**Per-post and per-channel error isolation.** `process_channel` advances `last_seen_id` only after a successful publish, so transient failures retry next cycle. But `TelegramBadRequest` is treated as permanent (the bot sent something Telegram rejects) — those advance state and skip, otherwise a single bad post would block the channel forever. The outer loop in `run()` catches all other exceptions per-channel so one failing channel doesn't stop the rest.

## Branches

- **`main`** — production. Currently deployed. The simple link-forwarding approach.
- **`telethon`** — alternative MTProto userbot implementation that does native `Forwarded from @channel` instead of links. Not deployed; the user couldn't obtain `API_ID`/`API_HASH` from my.telegram.org for the secondary account. Kept as a future option if API access becomes possible.

## Stale design docs

`docs/superpowers/specs/2026-05-05-tg-channel-mirror-design.md` and `docs/superpowers/plans/2026-05-05-tg-channel-mirror.md` describe an **earlier, richer** version of this service that recreated posts (parsed text/media, sanitized HTML, downloaded and re-uploaded photos/videos, deduplicated by text hash). That code was deleted when the service was simplified to link-forwarding. **Do not treat those docs as ground truth for current behavior.** They're kept only as historical context. Trust the code.

## Constraints to remember when changing things

- Source channels must be **public** (have `@username`). `t.me/s/<channel>` only works for public channels. There is no path to read private channels without a user/MTProto session.
- The bot must be **admin** in the target channel with "Post Messages" permission. Without it, every publish fails with `Forbidden`.
- `BOT_TOKEN` lives only in `.env` (gitignored) and Railway env vars. Never echo it to logs or commit it.
