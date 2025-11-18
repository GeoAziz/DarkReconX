"""Simple file-based JSON cache for API responses.

This cache stores JSON blobs under `.cache/` keyed by SHA256 of the
request key. Each entry includes a timestamp so TTLs can be honored.
"""
from pathlib import Path
import json
import time
import hashlib
from typing import Any, Optional


CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


def _key_to_path(key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{h}.json"


def get_cached(key: str, max_age: Optional[int] = None) -> Optional[Any]:
    p = _key_to_path(key)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        ts = data.get("_ts", 0)
        if max_age is not None and (time.time() - ts) > max_age:
            return None
        return data.get("value")
    except Exception:
        return None


def set_cached(key: str, value: Any) -> None:
    p = _key_to_path(key)
    payload = {"_ts": int(time.time()), "value": value}
    try:
        p.write_text(json.dumps(payload, default=str), encoding="utf-8")
    except Exception:
        # best-effort: don't raise on cache failures
        return
