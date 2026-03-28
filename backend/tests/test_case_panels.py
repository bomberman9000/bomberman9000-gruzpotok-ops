from unittest.mock import patch

from fastapi.testclient import TestClient

from app.services.ai.operator_action_hints import operator_action_hints


def test_operator_action_hints_contains_core_ids():
    h = operator_action_hints(call_id=9, request_id="req-1")
    ids = {x["id"] for x in h}
    for need in ("accept", "reject", "edit", "mark_useful", "mark_not_useful", "open_sources", "retry", "escalate"):
        assert need in ids


@patch("app.api.ai_operator_dashboard_routes.panel_for_claim")
def test_panel_claim(mock_panel, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_panel.return_value = {"panel_kind": "claim", "header": {"entity_id": "c1"}}
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/panels/claims/c1")
    assert r.status_code == 200
    assert r.json()["panel_kind"] == "claim"
