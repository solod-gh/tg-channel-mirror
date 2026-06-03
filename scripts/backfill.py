"""One-off helper: rewind each channel's last_seen_id so the bot re-forwards
recent posts it missed while down.

Lowers last_seen_id by N for every channel currently in the state DB. The next
poll cycle then treats the last ~N posts as "new" and forwards them. Capped at
what t.me/s/ still exposes (~20 most recent), so very old posts can't come back
even if N is large.

Usage (on the server, bot stopped):
    .venv/bin/python -m scripts.backfill 10
"""
import asyncio
import sys
from pathlib import Path

import aiosqlite

DB_PATH = Path("data/state.db")


async def main(n: int) -> None:
    if not DB_PATH.exists():
        print(f"No state DB at {DB_PATH}; nothing to do.")
        return

    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute(
            "SELECT channel, last_seen_id FROM channel_state ORDER BY channel"
        ) as cur:
            rows = await cur.fetchall()

        for channel, last_seen in rows:
            new_value = max(0, last_seen - n)
            await conn.execute(
                "UPDATE channel_state SET last_seen_id = ? WHERE channel = ?",
                (new_value, channel),
            )
            print(f"{channel}: {last_seen} -> {new_value}")
        await conn.commit()

    print(f"\nDone. Rewound {len(rows)} channels by {n}. "
          f"Restart the bot to forward the missed posts.")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    asyncio.run(main(n))
