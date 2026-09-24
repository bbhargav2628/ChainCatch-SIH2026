"""
Tiny file-based TTL cache for LIVE MODE lookups, so re-analyzing the same
wallet during a demo doesn't burn extra API quota or hit a rate limit.
Not a real database — this is a local SIH presentation prototype
(see CACHE_TTL_SECONDS in config.py / .env).
"""
import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def _path(chain: str, address: str) -> Path:
    d = CACHE_DIR / chain
    d.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in address if c.isalnum())[:80] or "unknown"
    return d / f"{safe}.json"


def get(chain: str, address: str, ttl_seconds: int):
    p = _path(chain, address)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if time.time() - payload.get("cached_at", 0) > ttl_seconds:
        return None
    return payload.get("data")


def set(chain: str, address: str, data) -> None:
    p = _path(chain, address)
    try:
        p.write_text(json.dumps({"cached_at": time.time(), "data": data}))
    except OSError:
        pass
