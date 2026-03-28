from __future__ import annotations

from pathlib import Path


def category_from_relative_path(rel: Path) -> str:
    s = str(rel).lower()
    if "legal" in s or "юр" in s or "pravo" in s:
        return "legal"
    if "freight" in s or "gruz" in s or "перевоз" in s or "logist" in s:
        return "freight"
    return "general"


def source_type_from_path(rel: Path) -> str:
    s = rel.as_posix().lower()
    # Тестовые и демо-пути (приёмка)
    if "examples/general" in s:
        return "internal"
    if "examples/legal" in s:
        return "law"
    if "examples/freight" in s:
        return "other"
    if "legal_pravo" in s or "legal_github" in s or "/law/" in s or "кодекс" in s:
        return "law"
    if "contract" in s or "договор" in s:
        return "contract"
    if "template" in s or "templates" in s:
        return "template"
    if "internal" in s or "внутр" in s:
        return "internal"
    return "other"
