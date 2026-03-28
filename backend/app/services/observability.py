from __future__ import annotations

import time
import logging
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)

_lock = Lock()
_state: dict[str, Any] = {
    "total_ai_calls": 0,
    "calls_by_status": {},
    "last_rag_available": True,
    "last_rag_error": None,
    "last_rag_error_at": None,
}


def note_call_completed(*, normalized_status: str, rag_reachable: bool, rag_error: str | None) -> None:
    with _lock:
        _state["total_ai_calls"] += 1
        _state["calls_by_status"][normalized_status] = int(_state["calls_by_status"].get(normalized_status, 0)) + 1
        if rag_reachable:
            _state["last_rag_available"] = True
            if rag_error is None:
                _state["last_rag_error"] = None
        else:
            _state["last_rag_available"] = False
            _state["last_rag_error"] = rag_error
            _state["last_rag_error_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            logger.warning(
                "rag unreachable status=%s error=%s",
                normalized_status,
                rag_error,
            )


def snapshot() -> dict[str, Any]:
    with _lock:
        return {
            "total_ai_calls": _state["total_ai_calls"],
            "calls_by_status": dict(_state["calls_by_status"]),
            "last_rag_available": _state["last_rag_available"],
            "last_rag_error": _state["last_rag_error"],
            "last_rag_error_at": _state["last_rag_error_at"],
        }


def reset_for_tests() -> None:
    with _lock:
        _state["total_ai_calls"] = 0
        _state["calls_by_status"] = {}
        _state["last_rag_available"] = True
        _state["last_rag_error"] = None
        _state["last_rag_error_at"] = None
