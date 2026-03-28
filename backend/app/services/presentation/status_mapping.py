from __future__ import annotations

from typing import Literal

Severity = Literal["info", "warning", "danger", "success"]

# Единые правила отображения (UI / Telegram)
STATUS_SEVERITY: dict[str, Severity] = {
    "ok": "success",
    "insufficient_data": "warning",
    "unavailable": "danger",
    "upstream_error": "danger",
    "disabled": "info",
    "invalid_upstream": "danger",
}

STATUS_LABEL_RU: dict[str, str] = {
    "ok": "Готово",
    "insufficient_data": "Недостаточно данных",
    "unavailable": "AI недоступен",
    "upstream_error": "Ошибка сервиса",
    "disabled": "Отключено",
    "invalid_upstream": "Некорректный ответ",
}

STATUS_BADGE: dict[str, str] = {
    "ok": "ok",
    "insufficient_data": "warn",
    "unavailable": "error",
    "upstream_error": "error",
    "disabled": "off",
    "invalid_upstream": "error",
}

RISK_SEVERITY: dict[str, Severity] = {
    "low": "success",
    "medium": "warning",
    "high": "danger",
}


def severity_for_normalized_status(status: str) -> Severity:
    return STATUS_SEVERITY.get(status, "info")


def label_for_status(status: str) -> str:
    return STATUS_LABEL_RU.get(status, status)


def badge_for_status(status: str) -> str:
    return STATUS_BADGE.get(status, "info")


def severity_for_risk_level(level: str | None) -> Severity | None:
    if not level:
        return None
    return RISK_SEVERITY.get(level.lower().strip(), "warning")


def effective_severity(
    *,
    normalized_status: str,
    risk_level: str | None,
) -> Severity:
    """При успешном risk-check приоритет у уровня риска."""
    if normalized_status == "ok" and risk_level:
        rs = severity_for_risk_level(risk_level)
        if rs:
            return rs
    return severity_for_normalized_status(normalized_status)
