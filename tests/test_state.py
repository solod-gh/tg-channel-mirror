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
