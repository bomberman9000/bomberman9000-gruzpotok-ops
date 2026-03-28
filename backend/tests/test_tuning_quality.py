from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.schemas.review_reasons import REVIEW_REASON_CODES, normalize_reason_codes
from app.services.ai.problem_cases_service import export_problem_cases
from app.services.ai.tuning_hints import build_tuning_hints_for_call, derive_quality_tuning_hints


def test_normalize_reason_codes_filters_unknown():
    assert normalize_reason_codes(["weak_citations", "nope", "weak_citations"]) == ["weak_citations"]


def test_all_reason_codes_documented():
    assert "other" in REVIEW_REASON_CODES
    assert "weak_citations" in REVIEW_REASON_CODES


def test_tuning_hints_for_call_weak_citations():
    h = build_tuning_hints_for_call(
        call_row={"normalized_status": "ok", "citations_count": 0, "endpoint": "e", "persona": "legal"},
        review_row={"review_reason_codes": ["weak_citations"]},
    )
    assert h.get("likely_primary_area") == "citations_retrieval"


def test_tuning_hints_bad_price_range_freight_logistics_message():
    h = build_tuning_hints_for_call(
        call_row={
            "normalized_status": "ok",
            "citations_count": 1,
            "endpoint": "freight/sales-reply",
            "persona": "logistics",
        },
        review_row={"review_reason_codes": ["bad_price_range"]},
    )
    messages = [x["message"] for x in h["hints"]]
    assert any("freight/logistics" in m for m in messages)
    assert any("широких вилок" in m for m in messages)


def test_derive_quality_tuning_hints_structure():
    out = derive_quality_tuning_hints(
        {
            "cases_needing_better_data": [{"endpoint": "claim_review", "count": 5}],
            "breakdown": {"by_reason": [{"reason": "weak_citations", "count": 3}]},
            "top_edited_reasons": [{"endpoint": "e", "reason": "weak_citations", "count": 2}],
            "cases_needing_prompt_or_rule_tuning": [],
        }
    )
    assert "scenarios_needing_better_citations" in out


@patch("app.services.ai.problem_cases_service.get_conn")
def test_export_problem_cases_empty_db(mock_get_conn, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from app.core.config import get_settings

    get_settings.cache_clear()
    r = export_problem_cases(
        date_from=None,
        date_to=None,
        persona=None,
        scenario=None,
        rejected_only=False,
        edited_only=False,
        insufficient_only=False,
        limit=10,
    )
    assert r.get("note") == "database_not_configured"


def test_reject_review_reason_codes_in_request(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()

    with patch("app.api.ai_review_routes.get_ai_call_by_id") as mock_call, patch(
        "app.api.ai_review_routes.upsert_review"
    ) as mock_up:
        mock_call.return_value = {
            "id": 9,
            "request_id": "r9",
            "normalized_status": "ok",
            "user_input_json": {},
        }
        mock_up.return_value = 1
        from app.main import app

        client = TestClient(app)
        res = client.post(
            "/api/v1/internal/ai/calls/9/reject",
            json={"reason": "bad", "reason_codes": ["weak_citations"]},
        )
        assert res.status_code == 200
        kwargs = mock_up.call_args.kwargs
        assert kwargs.get("review_reason_codes") == ["weak_citations"]


def test_problem_cases_export_route(monkeypatch):
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    with patch("app.api.ai_ops_hardening_routes.export_problem_cases") as mock_ex:
        mock_ex.return_value = {"items": [], "filters": {}}
        from app.main import app

        c = TestClient(app)
        r = c.get("/api/v1/internal/ai/export/problem-cases")
        assert r.status_code == 200
        mock_ex.assert_called_once()


def test_history_detail_includes_tuning_hints(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    monkeypatch.setenv("INTERNAL_AUTH_ENABLED", "false")
    from app.core.config import get_settings

    get_settings.cache_clear()
    with patch("app.api.ai_history_routes.get_ai_call_by_id") as gc, patch(
        "app.api.ai_history_routes.list_feedback_for_request"
    ) as lf, patch("app.api.ai_history_routes.get_review_by_call_id") as gr, patch(
        "app.api.ai_history_routes.build_review_ui_payload"
    ) as br:
        gc.return_value = {
            "id": 1,
            "request_id": "x",
            "normalized_status": "ok",
            "citations_count": 0,
            "endpoint": "claim_review",
            "persona": "legal",
            "user_input_json": {},
            "response_summary": "s",
        }
        lf.return_value = []
        gr.return_value = None
        br.return_value = {}
        from app.main import app

        r = TestClient(app).get("/api/v1/internal/ai/calls/1")
        assert r.status_code == 200
        body = r.json()
        assert "tuning_hints" in body
        assert body["tuning_hints"] is not None
