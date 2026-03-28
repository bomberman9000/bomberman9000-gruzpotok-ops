"""
Локальный журнал кейсов для post-rollout evaluation (JSON, без новых таблиц в БД).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path(__file__).resolve().parents[4] / "docs" / "evals" / "session_log.json"


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    """Загрузить список кейсов из JSON. Пустой или отсутствующий файл → []."""
    p = path or DEFAULT_LOG_PATH
    if not p.is_file():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("cases"), list):
        return [x for x in raw["cases"] if isinstance(x, dict)]
    return []


def save_cases(cases: list[dict[str, Any]], path: Path | None = None) -> None:
    p = path or DEFAULT_LOG_PATH
    _ensure_parent(p)
    payload = {"version": 1, "updated_at": _now_iso(), "cases": cases}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_case(
    case: dict[str, Any],
    *,
    path: Path | None = None,
    timestamp: str | None = None,
) -> list[dict[str, Any]]:
    """
    Добавить один кейс в журнал и сохранить файл.
    Если в case нет timestamp — подставляется текущий UTC ISO.
    """
    c = dict(case)
    if not c.get("timestamp"):
        c["timestamp"] = timestamp or _now_iso()
    cases = load_cases(path)
    cases.append(c)
    save_cases(cases, path=path)
    return cases


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
