from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_state (
    channel TEXT PRIMARY KEY,
    last_seen_id INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
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
