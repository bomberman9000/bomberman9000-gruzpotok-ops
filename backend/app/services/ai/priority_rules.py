from __future__ import annotations

from typing import Any


def score_review_queue_item(
    *,
    persona: str | None,
    mode: str | None,
    endpoint: str | None,
    normalized_status: str | None,
    llm_invoked: bool | None,
    risk_level: str | None,
    has_negative_feedback: bool,
    has_review: bool,
    operator_action: str | None,
) -> tuple[float, list[str]]:
    """
    Чем выше score — тем раньше в очереди.
    Правила продуктовые, без обращения к БД.
    """
    score = 0.0
    reasons: list[str] = []

    p = (persona or "").lower()
    st = (normalized_status or "").lower()
    ep = (endpoint or "").lower()
    rl = (risk_level or "").lower()

    if p == "legal":
        score += 40
        reasons.append("persona=legal")
    if p == "antifraud":
        score += 38
        reasons.append("persona=antifraud")
    if (mode or "").lower() == "strict" and llm_invoked is True:
        score += 15
        reasons.append("strict+llm")
    if rl == "high":
        score += 35
        reasons.append("risk=high")
    elif rl == "medium":
        score += 18
        reasons.append("risk=medium")
    if st == "insufficient_data":
        score += 25
        reasons.append("insufficient_data")
    if st == "unavailable":
        score += 12
        reasons.append("unavailable")
    if has_negative_feedback:
        score += 30
        reasons.append("negative_feedback")
    if has_review and operator_action in ("edited", "rejected"):
        score += 8
        reasons.append("pattern_edited_rejected")
    if not has_review:
        score += 20
        reasons.append("no_review_yet")
    else:
        score -= 25
        reasons.append("already_reviewed")

    if p == "logistics" and rl == "low" and st == "ok":
        score -= 15
        reasons.append("logistics_low_risk_ok")

    if "risk_check" in ep or "freight_risk" in ep:
        score += 5
        reasons.append("risk_endpoint")

    return float(score), reasons


def extract_risk_level_from_raw_data(raw_data: dict[str, Any] | None) -> str | None:
    """raw_data_json в БД — дамп UnifiedAIResponse; risk_level часто в raw_response."""
    if not raw_data or not isinstance(raw_data, dict):
        return None
    rr = raw_data.get("raw_response")
    if isinstance(rr, dict) and rr.get("risk_level"):
        return str(rr.get("risk_level"))
    return None


def risk_level_from_call_row(row: dict[str, Any]) -> str | None:
    raw = row.get("raw_data_json")
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except Exception:
            raw = None
    return extract_risk_level_from_raw_data(raw if isinstance(raw, dict) else None)
