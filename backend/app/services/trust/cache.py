from __future__ import annotations

import time
from typing import Any

_store: dict[str, tuple[Any, float]] = {}

DEFAULT_TTL = 60.0


def cache_key(subject_type: str, subject_id: str) -> str:
    return f"trust:profile:{subject_type}:{subject_id}"


def get(key: str) -> Any | None:
    entry = _store.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        del _store[key]
        return None
    return value


def set(key: str, value: Any, ttl_seconds: float = DEFAULT_TTL) -> None:
    _store[key] = (value, time.monotonic() + ttl_seconds)


def delete(key: str) -> None:
    _store.pop(key, None)


def clear() -> None:
    _store.clear()
