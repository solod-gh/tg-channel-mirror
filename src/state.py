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
