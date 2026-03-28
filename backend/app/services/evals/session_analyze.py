"""
Анализ локального session_log: подсчёты, TOP ISSUE, текстовые tuning hints (rule-based).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

TUNING_HINT_BY_REASON: dict[str, str] = {
    "bad_price_range": "проверить pricing logic или sales prompt",
    "too_generic": "ужесточить prompt, добавить структуру ответа",
    "insufficient_context": "усилить сбор обязательных данных",
    "weak_citations": "проверить retrieval и источники",
    "wrong_risk_level": "калибровка risk / persona / порогов",
    "incorrect_legal_basis": "усилить привязку к источникам и юридический промпт",
    "hallucination_suspected": "grounding, запрет утверждений без цитат",
    "bad_draft_tone": "тон и шаблон ответа",
    "formatting_problem": "формат вывода",
    "operator_preferred_manual": "продуктовый workflow / ручной контур",
    "other": "разобрать вручную по notes",
}

DEFAULT_TOP_ISSUE_THRESHOLD = 3


def canonical_operator_action(raw: object) -> str:
    """Единый ярлык: API даёт accepted/edited/rejected, в журнале часто accept/edit/reject."""
    s = str(raw or "").lower().strip()
    if s in ("accepted", "accept"):
        return "accept"
    if s in ("edited", "edit"):
        return "edit"
    if s in ("rejected", "reject"):
        return "reject"
    return s


def _case_operator_action(c: dict[str, Any]) -> str:
    for key in ("operator_action", "review_operator_action"):
        v = c.get(key)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return canonical_operator_action(s)
    return ""


def _flatten_reasons(cases: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for c in cases:
        rc = c.get("reason_codes")
        if isinstance(rc, list):
            for x in rc:
                s = str(x).strip()
                if s:
                    out.append(s)
    return out


def _useful_flag(c: dict[str, Any]) -> bool | None:
    u = c.get("useful")
    if isinstance(u, bool):
        return u
    return None


def analyze_cases(
    cases: list[dict[str, Any]],
    *,
    top_issue_threshold: int = DEFAULT_TOP_ISSUE_THRESHOLD,
) -> dict[str, Any]:
    if not cases:
        return {
            "counts": {},
            "top_rejected_reasons": [],
            "top_edited_reasons": [],
            "top_scenarios": [],
            "by_persona": {},
            "by_endpoint": {},
            "by_operator_action": {},
            "top_issue": None,
            "tuning_hints_lines": [],
            "text_report": "Нет кейсов в журнале.\n",
        }

    reason_counts = Counter(_flatten_reasons(cases))
    personas = [str(c.get("persona") or "") for c in cases]
    endpoints = [str(c.get("endpoint") or "") for c in cases]
    scenarios = [str(c.get("prompt_profile") or c.get("scenario") or "") for c in cases]

    op_actions: list[str] = []
    for c in cases:
        ca = _case_operator_action(c)
        if ca:
            op_actions.append(ca)

    by_op = Counter(op_actions)
    by_persona = Counter(p for p in personas if p)
    by_endpoint = Counter(e for e in endpoints if e)
    by_scenario = Counter(s for s in scenarios if s)

    rejected = [c for c in cases if _case_operator_action(c) == "reject"]
    edited = [c for c in cases if _case_operator_action(c) == "edit"]
    top_rej = Counter(_flatten_reasons(rejected)).most_common(20)
    top_ed = Counter(_flatten_reasons(edited)).most_common(20)
    top_scen = by_scenario.most_common(15)

    top_issue: dict[str, Any] | None = None
    for reason, n in reason_counts.most_common():
        if n >= top_issue_threshold:
            aff_ep = sorted({str(c.get("endpoint") or "") for c in cases if reason in (c.get("reason_codes") or [])})
            aff_per = sorted({str(c.get("persona") or "") for c in cases if reason in (c.get("reason_codes") or [])})
            top_issue = {
                "reason_code": reason,
                "count": n,
                "affected_endpoints": [e for e in aff_ep if e],
                "affected_personas": [p for p in aff_per if p],
            }
            break

    hints_lines: list[str] = []
    for r, n in reason_counts.most_common(10):
        hint = TUNING_HINT_BY_REASON.get(r, "смотреть notes и quality-report в БД")
        hints_lines.append(f"- {r} (x{n}): {hint}")

    lines_op = [f"  {k}: {v}" for k, v in sorted(by_op.items(), key=lambda x: -x[1])]
    lines_all_reasons = [f"  {k}: {v}" for k, v in reason_counts.most_common(15)]
    rej_lines = [f"  {k}: {v}" for k, v in top_rej[:10]] or ["  —"]
    ed_lines = [f"  {k}: {v}" for k, v in top_ed[:10]] or ["  —"]
    scen_lines = [f"  {k}: {v}" for k, v in top_scen[:10]] or ["  —"]

    lines: list[str] = [
        f"Кейсов: {len(cases)}",
        "",
        "По operator_action:",
        *lines_op,
        "",
        "Top reason_codes (все кейсы):",
        *lines_all_reasons,
        "",
        "top_rejected_reasons:",
        *rej_lines,
        "",
        "top_edited_reasons:",
        *ed_lines,
        "",
        "top scenarios (prompt_profile / scenario):",
        *scen_lines,
        "",
    ]
    if top_issue:
        lines.extend(
            [
                "TOP ISSUE:",
                f"  reason_code: {top_issue['reason_code']} (count={top_issue['count']} >= {top_issue_threshold})",
                f"  affected endpoints: {top_issue['affected_endpoints']}",
                f"  affected personas: {top_issue['affected_personas']}",
                "",
            ]
        )
    else:
        lines.append(
            f"TOP ISSUE: нет причины с частотой >= {top_issue_threshold} — соберите больше кейсов или снизьте порог.\n"
        )

    lines.append("Tuning hints (эвристика):")
    lines.extend(hints_lines or ["  —"])

    text_report = "\n".join(lines) + "\n"

    return {
        "counts": {
            "total": len(cases),
            "by_reason_code": dict(reason_counts),
            "by_operator_action": dict(by_op),
            "by_persona": dict(by_persona),
            "by_endpoint": dict(by_endpoint),
            "by_scenario": dict(by_scenario),
        },
        "top_rejected_reasons": [{"reason": k, "count": v} for k, v in top_rej],
        "top_edited_reasons": [{"reason": k, "count": v} for k, v in top_ed],
        "top_scenarios": [{"scenario": k, "count": v} for k, v in top_scen],
        "top_issue": top_issue,
        "tuning_hints_lines": hints_lines,
        "text_report": text_report,
    }
