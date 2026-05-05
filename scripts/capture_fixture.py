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
