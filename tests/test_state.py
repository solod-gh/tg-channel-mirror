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
