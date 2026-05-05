# TG Channel Mirror Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Зеркалить посты из ~10 публичных Telegram-каналов в личный приватный канал, без фильтрации содержимого.

**Architecture:** Один Python-процесс на Railway. Чтение через `https://t.me/s/<channel>` с HTML-парсингом, публикация через Bot API. Состояние (last_seen_id, dedup hashes) — в SQLite-файле. Без user-сессий, без LLM.

**Tech Stack:** Python 3.12, `httpx`, `selectolax`, `aiogram` 3.x, `aiosqlite`, `pytest`/`pytest-asyncio`.

**Spec:** [`docs/superpowers/specs/2026-05-05-tg-channel-mirror-design.md`](../specs/2026-05-05-tg-channel-mirror-design.md)

---

## File Structure

```
Telegram/
├── src/
│   ├── __init__.py
│   ├── config.py        # чтение env vars → Config dataclass
│   ├── state.py         # SQLite: last_seen_id + seen_hashes
│   ├── parser.py        # HTML → list[Post]
│   ├── publisher.py     # Post → Bot API send
│   └── main.py          # цикл опроса, склейка модулей
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── telegram_channel.html   # реальный снимок @telegram
│   │   ├── post_text_only.html     # синтетический фрагмент
│   │   ├── post_with_photo.html
│   │   ├── post_with_video.html
│   │   ├── post_album.html
│   │   └── post_long_text.html
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_parser.py
│   ├── test_publisher.py
│   └── test_main.py
├── data/                # gitignored, создаётся в рантайме
├── pyproject.toml
├── requirements.txt
├── Procfile             # Railway: `worker: python -m src.main`
├── runtime.txt          # python-3.12.x
├── .env.example
├── .gitignore
└── README.md
```

**Принципы декомпозиции:**

- `config.py` — чистое чтение env vars, не зависит ни от чего.
- `state.py` — единственный файл, знающий про SQLite. Все остальные модули общаются с ним через async-методы.
- `parser.py` — pure: HTML-строка → list[Post]. Никакого I/O, легко тестируется на фикстурах.
- `publisher.py` — обёртка над `aiogram.Bot`, единственное место с TG-side-effects.
- `main.py` — оркестратор: тянет HTML, дёргает parser, фильтрует через state, шлёт через publisher.

Каждый модуль ≤ 200 строк, единственная ответственность.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `.gitignore`, `.env.example`, `Procfile`, `runtime.txt`, `README.md`
- Create: `src/__init__.py`, `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Инициализировать git-репо**

```bash
cd /Users/daniilsolodovnikov/Documents/VSCode/Telegram
rm -f в  # пустой мусорный файл
git init
git branch -M main
```

- [ ] **Step 2: Создать `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.egg-info/

# Virtual env
.venv/
venv/

# Env / secrets
.env
.env.local

# Runtime data
data/
*.db
*.db-journal

# IDE
.vscode/
.idea/
.DS_Store
```

- [ ] **Step 3: Создать `requirements.txt`**

```
httpx==0.27.2
selectolax==0.3.21
aiogram==3.13.1
aiosqlite==0.20.0
python-dotenv==1.0.1
```

И dev-зависимости в `requirements-dev.txt`:

```
pytest==8.3.3
pytest-asyncio==0.24.0
respx==0.21.1
```

- [ ] **Step 4: Создать `pyproject.toml`**

```toml
[project]
name = "tg-channel-mirror"
version = "0.1.0"
description = "Mirror posts from public TG channels to a private channel via Bot API"
requires-python = ">=3.12"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.setuptools.packages.find]
where = ["."]
include = ["src*"]
```

- [ ] **Step 5: Создать `runtime.txt`**

```
python-3.12.7
```

- [ ] **Step 6: Создать `Procfile`**

```
worker: python -m src.main
```

- [ ] **Step 7: Создать `.env.example`**

```
BOT_TOKEN=123456:ABC-DEF...
CHANNEL_ID=-1001234567890
CHANNELS=durov,telegram
POLL_INTERVAL=60
DEDUP_WINDOW=24
```

- [ ] **Step 8: Создать `README.md`**

```markdown
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
```

- [ ] **Step 9: Создать пустые init-файлы**

`src/__init__.py`:
```python
```

`tests/__init__.py`:
```python
```

`tests/conftest.py`:
```python
import pytest
```

- [ ] **Step 10: Создать виртуальное окружение и поставить зависимости**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Ожидаемо: установка проходит без ошибок.

- [ ] **Step 11: Прогнать пустой pytest для проверки сетапа**

```bash
pytest
```

Ожидаемо: `no tests ran` (это успех на этом этапе).

- [ ] **Step 12: Коммит**

```bash
git add .gitignore .env.example Procfile runtime.txt pyproject.toml requirements.txt requirements-dev.txt README.md src/ tests/
git commit -m "chore: project scaffolding"
```

---

## Task 2: Config Module

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Написать падающий тест в `tests/test_config.py`**

```python
import pytest
from src.config import Config, load_config


def test_load_config_returns_dataclass(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", "durov,telegram")
    monkeypatch.delenv("POLL_INTERVAL", raising=False)
    monkeypatch.delenv("DEDUP_WINDOW", raising=False)

    cfg = load_config()

    assert cfg.bot_token == "abc"
    assert cfg.channel_id == "-1001234567890"
    assert cfg.channels == ["durov", "telegram"]
    assert cfg.poll_interval == 60
    assert cfg.dedup_window_hours == 24


def test_load_config_strips_whitespace_and_at_signs(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", " @durov , telegram , ")

    cfg = load_config()

    assert cfg.channels == ["durov", "telegram"]


def test_load_config_uses_overrides(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", "durov")
    monkeypatch.setenv("POLL_INTERVAL", "30")
    monkeypatch.setenv("DEDUP_WINDOW", "0")

    cfg = load_config()

    assert cfg.poll_interval == 30
    assert cfg.dedup_window_hours == 0


def test_load_config_raises_on_missing_required(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", "durov")

    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        load_config()


def test_load_config_raises_on_empty_channels(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    monkeypatch.setenv("CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("CHANNELS", "")

    with pytest.raises(RuntimeError, match="CHANNELS"):
        load_config()
```

- [ ] **Step 2: Прогнать тесты и убедиться, что падают**

```bash
pytest tests/test_config.py -v
```

Ожидаемо: `ModuleNotFoundError: No module named 'src.config'` или `ImportError`.

- [ ] **Step 3: Реализовать `src/config.py`**

```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    channel_id: str
    channels: list[str]
    poll_interval: int
    dedup_window_hours: int


def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN env var is required")

    channel_id = os.getenv("CHANNEL_ID", "").strip()
    if not channel_id:
        raise RuntimeError("CHANNEL_ID env var is required")

    channels_raw = os.getenv("CHANNELS", "").strip()
    channels = [c.strip().lstrip("@") for c in channels_raw.split(",") if c.strip()]
    if not channels:
        raise RuntimeError("CHANNELS env var must list at least one channel")

    poll_interval = int(os.getenv("POLL_INTERVAL", "60"))
    dedup_window_hours = int(os.getenv("DEDUP_WINDOW", "24"))

    return Config(
        bot_token=bot_token,
        channel_id=channel_id,
        channels=channels,
        poll_interval=poll_interval,
        dedup_window_hours=dedup_window_hours,
    )
```

- [ ] **Step 4: Прогнать тесты и убедиться, что проходят**

```bash
pytest tests/test_config.py -v
```

Ожидаемо: 5 passed.

- [ ] **Step 5: Коммит**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat(config): load and validate env vars"
```

---

## Task 3: State Module (SQLite)

**Files:**
- Create: `src/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Написать падающие тесты в `tests/test_state.py`**

```python
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.state import State


@pytest.fixture
async def state(tmp_path: Path):
    db_path = tmp_path / "test.db"
    s = State(db_path)
    await s.connect()
    yield s
    await s.close()


async def test_last_seen_id_returns_none_for_unknown_channel(state: State):
    assert await state.get_last_seen_id("durov") is None


async def test_set_then_get_last_seen_id(state: State):
    await state.set_last_seen_id("durov", 42)
    assert await state.get_last_seen_id("durov") == 42


async def test_set_last_seen_id_overwrites(state: State):
    await state.set_last_seen_id("durov", 10)
    await state.set_last_seen_id("durov", 20)
    assert await state.get_last_seen_id("durov") == 20


async def test_seen_hash_within_window(state: State):
    now = datetime.now(timezone.utc)
    await state.record_hash("abc123", "durov", now)
    assert await state.was_seen_recently("abc123", window_hours=24, now=now) is True


async def test_seen_hash_outside_window(state: State):
    old = datetime.now(timezone.utc) - timedelta(hours=48)
    now = datetime.now(timezone.utc)
    await state.record_hash("abc123", "durov", old)
    assert await state.was_seen_recently("abc123", window_hours=24, now=now) is False


async def test_unseen_hash_returns_false(state: State):
    now = datetime.now(timezone.utc)
    assert await state.was_seen_recently("never", window_hours=24, now=now) is False


async def test_dedup_window_zero_disables_check(state: State):
    now = datetime.now(timezone.utc)
    await state.record_hash("abc", "durov", now)
    assert await state.was_seen_recently("abc", window_hours=0, now=now) is False


async def test_cleanup_removes_old_hashes(state: State):
    old = datetime.now(timezone.utc) - timedelta(hours=48)
    fresh = datetime.now(timezone.utc)
    await state.record_hash("old_one", "durov", old)
    await state.record_hash("fresh_one", "durov", fresh)

    deleted = await state.cleanup_old_hashes(window_hours=24, now=fresh)

    assert deleted == 1
    assert await state.was_seen_recently("old_one", window_hours=24, now=fresh) is False
    assert await state.was_seen_recently("fresh_one", window_hours=24, now=fresh) is True


async def test_state_persists_across_reconnect(tmp_path: Path):
    db_path = tmp_path / "persist.db"

    s1 = State(db_path)
    await s1.connect()
    await s1.set_last_seen_id("durov", 99)
    await s1.close()

    s2 = State(db_path)
    await s2.connect()
    assert await s2.get_last_seen_id("durov") == 99
    await s2.close()
```

- [ ] **Step 2: Прогнать тесты, убедиться что падают**

```bash
pytest tests/test_state.py -v
```

Ожидаемо: ImportError.

- [ ] **Step 3: Реализовать `src/state.py`**

```python
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_state (
    channel TEXT PRIMARY KEY,
    last_seen_id INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS seen_hashes (
    hash TEXT PRIMARY KEY,
    first_channel TEXT NOT NULL,
    first_seen_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_seen_hashes_time ON seen_hashes(first_seen_at);
"""


class State:
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def get_last_seen_id(self, channel: str) -> int | None:
        assert self._conn is not None
        async with self._conn.execute(
            "SELECT last_seen_id FROM channel_state WHERE channel = ?",
            (channel,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

    async def set_last_seen_id(self, channel: str, message_id: int) -> None:
        assert self._conn is not None
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            """
            INSERT INTO channel_state (channel, last_seen_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(channel) DO UPDATE SET
                last_seen_id = excluded.last_seen_id,
                updated_at = excluded.updated_at
            """,
            (channel, message_id, now),
        )
        await self._conn.commit()

    async def record_hash(
        self, hash_: str, channel: str, when: datetime
    ) -> None:
        assert self._conn is not None
        await self._conn.execute(
            """
            INSERT OR IGNORE INTO seen_hashes (hash, first_channel, first_seen_at)
            VALUES (?, ?, ?)
            """,
            (hash_, channel, when.isoformat()),
        )
        await self._conn.commit()

    async def was_seen_recently(
        self, hash_: str, window_hours: int, now: datetime
    ) -> bool:
        if window_hours <= 0:
            return False
        assert self._conn is not None
        cutoff = (now.timestamp() - window_hours * 3600)
        async with self._conn.execute(
            "SELECT first_seen_at FROM seen_hashes WHERE hash = ?",
            (hash_,),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return False
            first_seen = datetime.fromisoformat(row[0])
            return first_seen.timestamp() >= cutoff

    async def cleanup_old_hashes(
        self, window_hours: int, now: datetime
    ) -> int:
        assert self._conn is not None
        cutoff_ts = now.timestamp() - window_hours * 3600
        cutoff_iso = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc).isoformat()
        cur = await self._conn.execute(
            "DELETE FROM seen_hashes WHERE first_seen_at < ?",
            (cutoff_iso,),
        )
        await self._conn.commit()
        return cur.rowcount or 0
```

- [ ] **Step 4: Прогнать тесты, убедиться что проходят**

```bash
pytest tests/test_state.py -v
```

Ожидаемо: 9 passed.

- [ ] **Step 5: Коммит**

```bash
git add src/state.py tests/test_state.py
git commit -m "feat(state): SQLite store for last_seen_id and dedup hashes"
```

---

## Task 4: Capture Real HTML Fixtures

**Files:**
- Create: `tests/fixtures/telegram_channel.html`
- Create: `scripts/capture_fixture.py`

Цель — получить реальный HTML с `t.me/s/telegram` и сохранить как fixture для тестов парсера. Это **не** unit-test, а одноразовая утилита.

- [ ] **Step 1: Создать скрипт захвата `scripts/capture_fixture.py`**

```python
"""Single-shot utility: download a t.me/s/<channel> page and save as fixture."""
import sys
from pathlib import Path

import httpx


def capture(channel: str, output: Path) -> None:
    url = f"https://t.me/s/{channel}"
    response = httpx.get(url, follow_redirects=True, timeout=30.0)
    response.raise_for_status()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(response.text, encoding="utf-8")
    print(f"Saved {len(response.text)} bytes to {output}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.capture_fixture <channel> <output_path>")
        sys.exit(1)
    capture(sys.argv[1], Path(sys.argv[2]))
```

- [ ] **Step 2: Создать `scripts/__init__.py`**

```python
```

- [ ] **Step 3: Захватить fixture**

```bash
python -m scripts.capture_fixture telegram tests/fixtures/telegram_channel.html
```

Ожидаемо: создан файл `tests/fixtures/telegram_channel.html` размером несколько сотен KB.

- [ ] **Step 4: Глянуть структуру для документации**

```bash
grep -o 'class="tgme_widget_message[^"]*"' tests/fixtures/telegram_channel.html | sort -u | head
grep -c 'data-post=' tests/fixtures/telegram_channel.html
```

Ожидаемо: видно классы вроде `tgme_widget_message`, `tgme_widget_message_text`, `tgme_widget_message_photo_wrap`. Постов — ~20.

- [ ] **Step 5: Коммит fixture и скрипта**

```bash
git add scripts/ tests/fixtures/telegram_channel.html
git commit -m "test: capture real t.me/s fixture from @telegram"
```

---

## Task 5: Parser — Basic Post Extraction

**Files:**
- Create: `src/parser.py`
- Create: `tests/test_parser.py`
- Create: `tests/fixtures/post_text_only.html`

`t.me/s/<channel>` использует следующие классы (зафиксированы по реальному HTML):

| Что              | Селектор                                                                  |
|------------------|---------------------------------------------------------------------------|
| Контейнер поста  | `div.tgme_widget_message[data-post]`                                      |
| ID поста         | атрибут `data-post`, формат `"<channel>/<id>"`                            |
| Текст            | `div.tgme_widget_message_text` (HTML внутри)                              |
| Время            | `time.time` атрибут `datetime`                                            |
| Прямая ссылка    | `a.tgme_widget_message_date` атрибут `href`                              |
| Фото             | `a.tgme_widget_message_photo_wrap`, URL в inline `style="background-image:url('...')"` |
| Видео            | `video.tgme_widget_message_video` атрибут `src`                          |
| Альбом-обёртка   | `div.tgme_widget_message_grouped_wrap`                                   |

- [ ] **Step 1: Создать минимальный синтетический fixture для текстового поста**

`tests/fixtures/post_text_only.html`:
```html
<div class="tgme_widget_message_wrap">
  <div class="tgme_widget_message" data-post="durov/123">
    <a class="tgme_widget_message_date" href="https://t.me/durov/123">
      <time class="time" datetime="2026-05-05T12:00:00+00:00">12:00</time>
    </a>
    <div class="tgme_widget_message_text">Hello, <b>world</b>!</div>
  </div>
</div>
```

- [ ] **Step 2: Написать падающие тесты в `tests/test_parser.py`**

```python
from pathlib import Path

from src.parser import Post, parse_posts


FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_text_only_post():
    posts = parse_posts(load("post_text_only.html"))

    assert len(posts) == 1
    p = posts[0]
    assert p.channel == "durov"
    assert p.message_id == 123
    assert p.text_html == "Hello, <b>world</b>!"
    assert p.link == "https://t.me/durov/123"
    assert p.photos == []
    assert p.videos == []
    assert p.grouped_id is None


def test_parse_real_telegram_channel_returns_posts():
    posts = parse_posts(load("telegram_channel.html"))

    assert len(posts) > 0
    for p in posts:
        assert p.channel == "telegram"
        assert p.message_id > 0
        assert p.link.startswith("https://t.me/telegram/")


def test_parse_real_telegram_channel_posts_sorted_by_id():
    posts = parse_posts(load("telegram_channel.html"))
    ids = [p.message_id for p in posts]
    assert ids == sorted(ids), "posts should be returned in ascending id order"
```

- [ ] **Step 3: Прогнать тесты, убедиться что падают**

```bash
pytest tests/test_parser.py -v
```

Ожидаемо: ImportError.

- [ ] **Step 4: Реализовать `src/parser.py` (минимум для прохождения тестов)**

```python
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
```

- [ ] **Step 5: Прогнать тесты, убедиться что проходят**

```bash
pytest tests/test_parser.py -v
```

Ожидаемо: 3 passed.

- [ ] **Step 6: Коммит**

```bash
git add src/parser.py tests/test_parser.py tests/fixtures/post_text_only.html
git commit -m "feat(parser): extract text posts from t.me/s HTML"
```

---

## Task 6: Parser — Media Extraction

**Files:**
- Modify: `src/parser.py`
- Modify: `tests/test_parser.py`
- Create: `tests/fixtures/post_with_photo.html`
- Create: `tests/fixtures/post_with_video.html`
- Create: `tests/fixtures/post_album.html`

- [ ] **Step 1: Создать fixture с фото**

`tests/fixtures/post_with_photo.html`:
```html
<div class="tgme_widget_message" data-post="durov/200">
  <a class="tgme_widget_message_date" href="https://t.me/durov/200"></a>
  <a class="tgme_widget_message_photo_wrap"
     style="background-image:url('https://cdn4.cdn-telegram.org/file/photo123.jpg')"
     href="https://t.me/durov/200?single"></a>
  <div class="tgme_widget_message_text">photo caption</div>
</div>
```

- [ ] **Step 2: Создать fixture с видео**

`tests/fixtures/post_with_video.html`:
```html
<div class="tgme_widget_message" data-post="durov/201">
  <a class="tgme_widget_message_date" href="https://t.me/durov/201"></a>
  <a class="tgme_widget_message_video_player">
    <video class="tgme_widget_message_video"
           src="https://cdn4.cdn-telegram.org/file/video123.mp4"></video>
  </a>
  <div class="tgme_widget_message_text">video caption</div>
</div>
```

- [ ] **Step 3: Создать fixture с альбомом**

`tests/fixtures/post_album.html`:
```html
<div class="tgme_widget_message" data-post="durov/300">
  <a class="tgme_widget_message_date" href="https://t.me/durov/300"></a>
  <div class="tgme_widget_message_grouped_wrap" data-grouped-id="123456789">
    <a class="tgme_widget_message_photo_wrap"
       style="background-image:url('https://cdn4.cdn-telegram.org/file/p1.jpg')"
       href="https://t.me/durov/300?single"></a>
    <a class="tgme_widget_message_photo_wrap"
       style="background-image:url('https://cdn4.cdn-telegram.org/file/p2.jpg')"
       href="https://t.me/durov/300?single"></a>
  </div>
  <div class="tgme_widget_message_text">album caption</div>
</div>
```

- [ ] **Step 4: Добавить тесты в `tests/test_parser.py`**

```python
def test_parse_post_with_photo():
    posts = parse_posts(load("post_with_photo.html"))
    assert len(posts) == 1
    p = posts[0]
    assert p.photos == ["https://cdn4.cdn-telegram.org/file/photo123.jpg"]
    assert p.videos == []
    assert p.text_html == "photo caption"


def test_parse_post_with_video():
    posts = parse_posts(load("post_with_video.html"))
    assert len(posts) == 1
    p = posts[0]
    assert p.videos == ["https://cdn4.cdn-telegram.org/file/video123.mp4"]
    assert p.photos == []


def test_parse_album():
    posts = parse_posts(load("post_album.html"))
    assert len(posts) == 1
    p = posts[0]
    assert p.grouped_id == "123456789"
    assert p.photos == [
        "https://cdn4.cdn-telegram.org/file/p1.jpg",
        "https://cdn4.cdn-telegram.org/file/p2.jpg",
    ]
```

- [ ] **Step 5: Прогнать новые тесты, убедиться что падают**

```bash
pytest tests/test_parser.py -v -k "photo or video or album"
```

Ожидаемо: 3 теста падают (текущая реализация не извлекает media).

- [ ] **Step 6: Расширить `_parse_one` в `src/parser.py`**

Заменить функцию `_parse_one` на:

```python
import re

_BG_URL_RE = re.compile(r"background-image\s*:\s*url\(['\"]?([^'\")]+)['\"]?\)")


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

    photos: list[str] = []
    for photo_node in node.css("a.tgme_widget_message_photo_wrap"):
        style = photo_node.attributes.get("style", "")
        m = _BG_URL_RE.search(style)
        if m:
            photos.append(m.group(1))

    videos: list[str] = []
    for video_node in node.css("video.tgme_widget_message_video"):
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
```

- [ ] **Step 7: Прогнать все тесты парсера**

```bash
pytest tests/test_parser.py -v
```

Ожидаемо: 6 passed (3 старых + 3 новых).

- [ ] **Step 8: Коммит**

```bash
git add src/parser.py tests/test_parser.py tests/fixtures/post_with_photo.html tests/fixtures/post_with_video.html tests/fixtures/post_album.html
git commit -m "feat(parser): extract photos, videos, and albums"
```

---

## Task 7: Publisher — Sending via Bot API

**Files:**
- Create: `src/publisher.py`
- Create: `tests/test_publisher.py`

`aiogram.Bot` ходит в TG напрямую. Для тестов мокаем `Bot` через `unittest.mock`.

- [ ] **Step 1: Написать падающие тесты в `tests/test_publisher.py`**

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.parser import Post
from src.publisher import Publisher, build_caption, split_long_text, MAX_TEXT


def make_post(**kwargs) -> Post:
    defaults = dict(
        channel="durov",
        message_id=1,
        text_html="hello",
        link="https://t.me/durov/1",
        photos=[],
        videos=[],
        grouped_id=None,
    )
    defaults.update(kwargs)
    return Post(**defaults)


def test_build_caption_appends_attribution():
    p = make_post(text_html="hello")
    caption = build_caption(p)
    assert "hello" in caption
    assert '<a href="https://t.me/durov/1">📡 @durov</a>' in caption


def test_build_caption_handles_empty_text():
    p = make_post(text_html="")
    caption = build_caption(p)
    assert caption.startswith('<a href="')
    assert "@durov" in caption


def test_split_long_text_under_limit_returns_single_chunk():
    text = "short text"
    assert split_long_text(text) == ["short text"]


def test_split_long_text_splits_on_paragraph_boundary():
    para_a = "A" * 2000
    para_b = "B" * 2000
    para_c = "C" * 2000
    text = f"{para_a}\n\n{para_b}\n\n{para_c}"
    chunks = split_long_text(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= MAX_TEXT


def test_split_long_text_hard_splits_when_no_paragraphs():
    text = "X" * (MAX_TEXT + 100)
    chunks = split_long_text(text)
    assert len(chunks) == 2
    assert "".join(chunks) == text


@pytest.fixture
def bot_mock():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_video = AsyncMock()
    bot.send_media_group = AsyncMock()
    return bot


async def test_publish_text_only_post(bot_mock):
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(text_html="just text"))

    bot_mock.send_message.assert_awaited_once()
    kwargs = bot_mock.send_message.await_args.kwargs
    assert kwargs["chat_id"] == "-100123"
    assert "just text" in kwargs["text"]
    assert "@durov" in kwargs["text"]


async def test_publish_single_photo_uses_send_photo(bot_mock):
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(
        text_html="cap",
        photos=["https://cdn/p.jpg"],
    ))

    bot_mock.send_photo.assert_awaited_once()
    bot_mock.send_message.assert_not_awaited()
    kwargs = bot_mock.send_photo.await_args.kwargs
    assert kwargs["photo"] == "https://cdn/p.jpg"
    assert "cap" in kwargs["caption"]


async def test_publish_single_video_uses_send_video(bot_mock):
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(
        text_html="cap",
        videos=["https://cdn/v.mp4"],
    ))

    bot_mock.send_video.assert_awaited_once()


async def test_publish_album_uses_send_media_group(bot_mock):
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(
        text_html="album",
        photos=["https://cdn/p1.jpg", "https://cdn/p2.jpg"],
        grouped_id="555",
    ))

    bot_mock.send_media_group.assert_awaited_once()
    bot_mock.send_photo.assert_not_awaited()
    media = bot_mock.send_media_group.await_args.kwargs["media"]
    assert len(media) == 2


async def test_publish_long_text_sends_multiple_messages(bot_mock):
    long_text = ("X" * 5000)
    pub = Publisher(bot=bot_mock, chat_id="-100123")
    await pub.publish(make_post(text_html=long_text))

    assert bot_mock.send_message.await_count >= 2
```

- [ ] **Step 2: Прогнать тесты, убедиться что падают**

```bash
pytest tests/test_publisher.py -v
```

Ожидаемо: ImportError.

- [ ] **Step 3: Реализовать `src/publisher.py`**

```python
from typing import Any

from aiogram import Bot
from aiogram.types import InputMediaPhoto, InputMediaVideo

from src.parser import Post


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
    return chunks


class Publisher:
    def __init__(self, bot: Bot, chat_id: str):
        self._bot = bot
        self._chat_id = chat_id

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
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=chunk,
                parse_mode="HTML",
                disable_web_page_preview=False,
            )

    async def _send_photo(self, post: Post) -> None:
        caption = build_caption(post)
        if len(caption) > MAX_CAPTION:
            await self._bot.send_photo(
                chat_id=self._chat_id,
                photo=post.photos[0],
            )
            for chunk in split_long_text(caption):
                await self._bot.send_message(
                    chat_id=self._chat_id,
                    text=chunk,
                    parse_mode="HTML",
                )
        else:
            await self._bot.send_photo(
                chat_id=self._chat_id,
                photo=post.photos[0],
                caption=caption,
                parse_mode="HTML",
            )

    async def _send_video(self, post: Post) -> None:
        caption = build_caption(post)
        if len(caption) > MAX_CAPTION:
            await self._bot.send_video(
                chat_id=self._chat_id,
                video=post.videos[0],
            )
            for chunk in split_long_text(caption):
                await self._bot.send_message(
                    chat_id=self._chat_id,
                    text=chunk,
                    parse_mode="HTML",
                )
        else:
            await self._bot.send_video(
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

        await self._bot.send_media_group(
            chat_id=self._chat_id,
            media=media,
        )
        if len(caption) > MAX_CAPTION:
            for chunk in split_long_text(caption):
                await self._bot.send_message(
                    chat_id=self._chat_id,
                    text=chunk,
                    parse_mode="HTML",
                )
```

- [ ] **Step 4: Прогнать тесты, убедиться что проходят**

```bash
pytest tests/test_publisher.py -v
```

Ожидаемо: 9 passed.

- [ ] **Step 5: Коммит**

```bash
git add src/publisher.py tests/test_publisher.py
git commit -m "feat(publisher): send posts via Bot API with media and long-text support"
```

---

## Task 8: Main Loop — Wire Everything Together

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Написать падающие тесты в `tests/test_main.py`**

```python
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.main import process_channel
from src.parser import Post
from src.state import State


def make_post(channel="durov", message_id=1, text="hi") -> Post:
    return Post(
        channel=channel,
        message_id=message_id,
        text_html=text,
        link=f"https://t.me/{channel}/{message_id}",
        photos=[],
        videos=[],
        grouped_id=None,
    )


@pytest.fixture
async def state(tmp_path: Path):
    s = State(tmp_path / "test.db")
    await s.connect()
    yield s
    await s.close()


async def test_first_run_sets_baseline_without_publishing(state: State):
    fetched = [make_post(message_id=10), make_post(message_id=11), make_post(message_id=12)]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    published_count = await process_channel(
        channel="durov",
        fetcher=fetcher,
        publisher=publisher,
        state=state,
        dedup_window_hours=24,
        now=datetime.now(timezone.utc),
    )

    assert published_count == 0
    publisher.publish.assert_not_awaited()
    assert await state.get_last_seen_id("durov") == 12


async def test_subsequent_run_publishes_only_new_posts(state: State):
    await state.set_last_seen_id("durov", 10)

    fetched = [make_post(message_id=10), make_post(message_id=11), make_post(message_id=12)]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    published_count = await process_channel(
        channel="durov",
        fetcher=fetcher,
        publisher=publisher,
        state=state,
        dedup_window_hours=24,
        now=datetime.now(timezone.utc),
    )

    assert published_count == 2
    assert publisher.publish.await_count == 2
    published_ids = [
        call.args[0].message_id for call in publisher.publish.await_args_list
    ]
    assert published_ids == [11, 12]
    assert await state.get_last_seen_id("durov") == 12


async def test_dedup_skips_post_with_same_text_from_another_channel(state: State):
    now = datetime.now(timezone.utc)
    await state.set_last_seen_id("durov", 10)
    await state.set_last_seen_id("other", 100)

    from src.main import _hash_text
    duplicate_text = "exact same body"
    await state.record_hash(_hash_text(duplicate_text), "other", now)

    fetched = [make_post(channel="durov", message_id=11, text=duplicate_text)]
    fetcher = AsyncMock(return_value=fetched)
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    published_count = await process_channel(
        channel="durov",
        fetcher=fetcher,
        publisher=publisher,
        state=state,
        dedup_window_hours=24,
        now=now,
    )

    assert published_count == 0
    publisher.publish.assert_not_awaited()
    assert await state.get_last_seen_id("durov") == 11


async def test_fetcher_failure_does_not_advance_state(state: State):
    await state.set_last_seen_id("durov", 10)

    fetcher = AsyncMock(side_effect=RuntimeError("network down"))
    publisher = MagicMock()
    publisher.publish = AsyncMock()

    with pytest.raises(RuntimeError):
        await process_channel(
            channel="durov",
            fetcher=fetcher,
            publisher=publisher,
            state=state,
            dedup_window_hours=24,
            now=datetime.now(timezone.utc),
        )

    assert await state.get_last_seen_id("durov") == 10
```

- [ ] **Step 2: Прогнать тесты, убедиться что падают**

```bash
pytest tests/test_main.py -v
```

Ожидаемо: ImportError.

- [ ] **Step 3: Реализовать `src/main.py`**

```python
import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable

import httpx
from aiogram import Bot

from src.config import Config, load_config
from src.parser import Post, parse_posts
from src.publisher import Publisher
from src.state import State


logger = logging.getLogger("mirror")

DB_PATH = Path("data/state.db")
HASH_PREFIX_LEN = 200


PostFetcher = Callable[[], Awaitable[list[Post]]]


def _hash_text(text: str) -> str:
    snippet = text.strip()[:HASH_PREFIX_LEN]
    return hashlib.sha256(snippet.encode("utf-8")).hexdigest()


async def fetch_channel_html(client: httpx.AsyncClient, channel: str) -> str:
    response = await client.get(f"https://t.me/s/{channel}", timeout=30.0)
    response.raise_for_status()
    return response.text


def make_fetcher(client: httpx.AsyncClient, channel: str) -> PostFetcher:
    async def _fetch() -> list[Post]:
        html = await fetch_channel_html(client, channel)
        return parse_posts(html)
    return _fetch


async def process_channel(
    channel: str,
    fetcher: PostFetcher,
    publisher: Publisher,
    state: State,
    dedup_window_hours: int,
    now: datetime,
) -> int:
    posts = await fetcher()
    if not posts:
        return 0

    last_seen = await state.get_last_seen_id(channel)
    is_first_run = last_seen is None
    max_id_in_batch = max(p.message_id for p in posts)

    if is_first_run:
        await state.set_last_seen_id(channel, max_id_in_batch)
        logger.info("First run for %s: baseline set to %d", channel, max_id_in_batch)
        return 0

    new_posts = [p for p in posts if p.message_id > last_seen]
    new_posts.sort(key=lambda p: p.message_id)

    published = 0
    for post in new_posts:
        text_for_hash = post.text_html or ""
        if text_for_hash:
            h = _hash_text(text_for_hash)
            if await state.was_seen_recently(h, dedup_window_hours, now):
                logger.info("Dedup skip: %s/%d", channel, post.message_id)
                await state.set_last_seen_id(channel, post.message_id)
                continue
            await state.record_hash(h, channel, now)

        try:
            await publisher.publish(post)
            published += 1
            await state.set_last_seen_id(channel, post.message_id)
        except Exception:
            logger.exception("Failed to publish %s/%d", channel, post.message_id)
            raise

    return published


async def cleanup_loop(state: State, window_hours: int, interval_seconds: int = 3600) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            now = datetime.now(timezone.utc)
            deleted = await state.cleanup_old_hashes(window_hours, now)
            if deleted:
                logger.info("Cleanup: removed %d old hashes", deleted)
        except Exception:
            logger.exception("Cleanup task failed")


async def run(config: Config) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    state = State(DB_PATH)
    await state.connect()

    bot = Bot(token=config.bot_token)
    publisher = Publisher(bot=bot, chat_id=config.channel_id)

    cleanup = asyncio.create_task(
        cleanup_loop(state, config.dedup_window_hours)
    )

    try:
        async with httpx.AsyncClient() as client:
            while True:
                cycle_start = datetime.now(timezone.utc)
                for channel in config.channels:
                    try:
                        await process_channel(
                            channel=channel,
                            fetcher=make_fetcher(client, channel),
                            publisher=publisher,
                            state=state,
                            dedup_window_hours=config.dedup_window_hours,
                            now=datetime.now(timezone.utc),
                        )
                    except Exception:
                        logger.exception("Channel %s failed; continuing", channel)
                elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
                sleep_for = max(0.0, config.poll_interval - elapsed)
                await asyncio.sleep(sleep_for)
    finally:
        cleanup.cancel()
        await bot.session.close()
        await state.close()


def main() -> None:
    config = load_config()
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Прогнать тесты, убедиться что проходят**

```bash
pytest tests/test_main.py -v
```

Ожидаемо: 4 passed.

- [ ] **Step 5: Прогнать весь test suite**

```bash
pytest -v
```

Ожидаемо: все тесты зелёные (~31 passed).

- [ ] **Step 6: Коммит**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat(main): orchestration loop with dedup and first-run baseline"
```

---

## Task 9: Local Smoke Test

**Files:** только конфиг.

Прежде чем деплоить — убедимся, что скрипт реально работает локально с настоящими каналами и реальным ботом.

- [ ] **Step 1: Заполнить `.env` локально**

```bash
cp .env.example .env
```

Отредактировать `.env`:
- `BOT_TOKEN` — токен из @BotFather
- `CHANNEL_ID` — ID приватного канала (см. ниже как узнать)
- `CHANNELS` — пара публичных каналов для теста, например `durov,telegram`

Чтобы узнать `CHANNEL_ID`: переслать любое сообщение из канала в @userinfobot — он вернёт `id` вида `-1001234567890`.

- [ ] **Step 2: Запустить скрипт**

```bash
source .venv/bin/activate
python -m src.main
```

Ожидаемо: в логах видно `First run for durov: baseline set to ...`, постов в канал не льётся.

- [ ] **Step 3: Подождать новый пост**

Дождаться появления нового поста в одном из источников (или временно выставить `CHANNELS=канал-где-часто-постят`). В логах должно появиться сообщение о публикации, в личном канале — сам пост с атрибуцией `📡 @channel`.

- [ ] **Step 4: Остановить скрипт (`Ctrl+C`), перезапустить**

Ожидаемо: на втором запуске `last_seen_id` уже сохранён, скрипт продолжает с него и не льёт старые посты заново.

- [ ] **Step 5: Если что-то не работает — debug**

Типичные проблемы:
- `Forbidden: bot was kicked from the channel` → бот не админ или не добавлен.
- `Bad Request: chat not found` → неверный `CHANNEL_ID` (должен начинаться с `-100`).
- `httpx.HTTPStatusError 404` для канала → канал приватный или имя написано неверно.
- В канал не приходит ничего → проверить `last_seen_id` в `data/state.db` (`sqlite3 data/state.db "select * from channel_state"`).

После того как локально всё работает — коммитить нечего, переходим к деплою.

---

## Task 10: Deploy to Railway

**Files:** уже всё на месте (`Procfile`, `runtime.txt`, `requirements.txt`).

- [ ] **Step 1: Создать GitHub-репо**

Через `gh`:
```bash
gh repo create tg-channel-mirror --private --source=. --remote=origin --push
```

Или вручную: создать репо на github.com, добавить remote, запушить.

- [ ] **Step 2: Зарегистрироваться на Railway** (railway.app), залогиниться через GitHub.

- [ ] **Step 3: New Project → Deploy from GitHub repo → выбрать `tg-channel-mirror`**

Railway сам определит Python-проект через nixpacks.

- [ ] **Step 4: Project → Variables: добавить env vars**

```
BOT_TOKEN=...
CHANNEL_ID=-1001234567890
CHANNELS=durov,telegram,...
POLL_INTERVAL=60
DEDUP_WINDOW=24
```

- [ ] **Step 5: Project → Settings → проверить, что используется Procfile worker process** (а не web). Если Railway по умолчанию запускает web — указать start command вручную: `python -m src.main`.

- [ ] **Step 6: Дождаться деплоя, открыть Logs**

Ожидаемо: те же логи, что были локально — `First run for ... baseline set to ...`.

- [ ] **Step 7: Проверить, что новые посты появляются в твоём канале**

Дождаться нового поста в одном из источников, убедиться что он появился в личном канале с атрибуцией.

- [ ] **Step 8 (опционально): Persistent storage для SQLite**

Railway пересоздаёт контейнер при каждом деплое, и `data/state.db` теряется. Это означает: после редеплоя скрипт думает, что это первый запуск, и **не дублирует** старые посты (это ок). Но dedup-окно сбрасывается.

Если нужна персистентность — Railway → Add Volume → mount path `/app/data`. Это всё.

- [ ] **Step 9: Финальный коммит README с реальным URL Railway**

Если в README хочется упомянуть, где смотреть логи / как редеплоить — добавить пару строк, закоммитить, запушить.

```bash
git add README.md
git commit -m "docs: deploy notes"
git push
```

---

## Done Criteria

- ✅ Все unit-тесты зелёные (`pytest`).
- ✅ Локальный запуск: на первом старте устанавливает baseline, на втором — публикует только новые посты.
- ✅ В Railway crashed = false, логи показывают цикл опроса каждые 60 сек.
- ✅ В личном канале появляются посты из источников с атрибуцией `📡 @channel`, ведущей на оригинал.
- ✅ Перезапуск скрипта не дублирует уже опубликованные посты.

## Out of Scope (см. spec)

- Фильтрация рекламы (LLM, regex, классификация).
- Self-learning кнопками.
- Поддержка приватных каналов.
- Web UI / админка.
- Опросы как опросы (отправляются как текст со ссылкой).
