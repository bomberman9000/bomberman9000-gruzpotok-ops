from __future__ import annotations

from app.services.evals.session_analyze import analyze_cases


def test_analyze_empty():
    r = analyze_cases([])
    assert "Нет кейсов" in r["text_report"]
    assert r["top_issue"] is None


def test_count_by_reason_and_top_issue():
    cases = [
        {
            "request_id": "1",
            "endpoint": "claim_review",
            "persona": "legal",
            "operator_action": "rejected",
            "reason_codes": ["too_generic", "weak_citations"],
        },
        {
            "request_id": "2",
            "endpoint": "claim_review",
            "persona": "legal",
            "operator_action": "rejected",
            "reason_codes": ["too_generic"],
        },
        {
            "request_id": "3",
            "endpoint": "freight",
            "persona": "logistics",
            "operator_action": "edited",
            "reason_codes": ["too_generic"],
        },
    ]
    r = analyze_cases(cases, top_issue_threshold=3)
    assert r["counts"]["by_reason_code"]["too_generic"] == 3
    assert r["top_issue"] is not None
    assert r["top_issue"]["reason_code"] == "too_generic"
    assert "claim_review" in r["top_issue"]["affected_endpoints"]
    assert "legal" in r["top_issue"]["affected_personas"]
    assert any("too_generic" in line for line in r["tuning_hints_lines"])


def test_top_rejected_vs_edited():
    cases = [
        {"operator_action": "rejected", "reason_codes": ["bad_price_range"], "endpoint": "a"},
        {"operator_action": "edited", "reason_codes": ["formatting_problem"], "endpoint": "b"},
    ]
    r = analyze_cases(cases, top_issue_threshold=5)
    rej = {x["reason"] for x in r["top_rejected_reasons"]}
    ed = {x["reason"] for x in r["top_edited_reasons"]}
    assert "bad_price_range" in rej
    assert "formatting_problem" in ed


def test_operator_action_aliases_and_review_fallback():
    cases = [
        {"operator_action": "accepted", "reason_codes": [], "endpoint": "x"},
        {"operator_action": "", "review_operator_action": "Rejected", "reason_codes": ["x"], "endpoint": "y"},
    ]
    r = analyze_cases(cases, top_issue_threshold=99)
    assert r["counts"]["by_operator_action"]["accept"] == 1
    assert r["counts"]["by_operator_action"]["reject"] == 1
    assert {x["reason"] for x in r["top_rejected_reasons"]} == {"x"}
