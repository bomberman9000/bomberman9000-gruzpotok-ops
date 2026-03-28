from __future__ import annotations

REVIEW_REASON_CODES: frozenset[str] = frozenset(
    {
        "insufficient_context",
        "wrong_risk_level",
        "weak_citations",
        "bad_draft_tone",
        "incorrect_legal_basis",
        "too_generic",
        "hallucination_suspected",
        "formatting_problem",
        "operator_preferred_manual",
        "bad_price_range",
        "other",
    }
)


def normalize_reason_codes(raw: list[str] | None) -> list[str]:
    """Фильтрация неизвестных кодов, порядок сохраняется, дубликаты убираются."""
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for x in raw:
        s = str(x).strip()
        if not s or s not in REVIEW_REASON_CODES:
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out
