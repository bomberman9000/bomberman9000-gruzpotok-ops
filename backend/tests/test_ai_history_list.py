from unittest.mock import patch

from fastapi.testclient import TestClient


def test_history_list_empty_without_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/calls")
    assert r.status_code == 200
    assert r.json() == []


@patch("app.api.ai_history_routes.list_ai_calls")
def test_history_list_with_filters(mock_list, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_list.return_value = [
        {
            "id": 1,
            "created_at": "2020-01-01T00:00:00",
            "request_id": "a",
            "endpoint": "query",
            "persona": "legal",
            "mode": "strict",
            "normalized_status": "ok",
            "llm_invoked": True,
            "citations_count": 1,
            "response_summary": "s",
            "latency_ms": 10,
            "is_error": False,
            "user_input_json": {},
        }
    ]
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/v1/internal/ai/calls", params={"persona": "legal"})
    assert r.status_code == 200
    assert r.json()[0]["request_id"] == "a"
    mock_list.assert_called_once()
