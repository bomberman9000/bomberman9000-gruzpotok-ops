from app.services.ai.priority_rules import (
    extract_risk_level_from_raw_data,
    risk_level_from_call_row,
    score_review_queue_item,
)


def test_score_legal_high_risk():
    s, reasons = score_review_queue_item(
        persona="legal",
        mode="strict",
        endpoint="x",
        normalized_status="ok",
        llm_invoked=True,
        risk_level="high",
        has_negative_feedback=False,
        has_review=False,
        operator_action=None,
    )
    assert s > 50
    assert "persona=legal" in reasons
    assert "risk=high" in reasons
    assert "no_review_yet" in reasons


def test_score_negative_feedback_boost():
    s1, _ = score_review_queue_item(
        persona="logistics",
        mode=None,
        endpoint="y",
        normalized_status="ok",
        llm_invoked=False,
        risk_level="low",
        has_negative_feedback=False,
        has_review=False,
        operator_action=None,
    )
    s2, r2 = score_review_queue_item(
        persona="logistics",
        mode=None,
        endpoint="y",
        normalized_status="ok",
        llm_invoked=False,
        risk_level="low",
        has_negative_feedback=True,
        has_review=False,
        operator_action=None,
    )
    assert s2 > s1
    assert "negative_feedback" in r2


def test_extract_risk_from_raw_data():
    raw = {"raw_response": {"risk_level": "high"}}
    assert extract_risk_level_from_raw_data(raw) == "high"


def test_risk_level_from_call_row():
    row = {"raw_data_json": {"raw_response": {"risk_level": "medium"}}}
    assert risk_level_from_call_row(row) == "medium"
