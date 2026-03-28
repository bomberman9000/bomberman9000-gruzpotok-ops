from unittest.mock import patch

from fastapi.testclient import TestClient


@patch("app.api.ai_history_routes.list_ai_calls")
def test_calls_passes_search_params(mock_list, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_list.return_value = []
    from app.main import app

    client = TestClient(app)
    r = client.get(
        "/api/v1/internal/ai/calls",
        params={
            "q": "hello",
            "entity_type": "claim",
            "entity_id": "c1",
            "reviewed_by": "op1",
        },
    )
    assert r.status_code == 200
    kwargs = mock_list.call_args.kwargs
    assert kwargs["q"] == "hello"
    assert kwargs["entity_type"] == "claim"
    assert kwargs["entity_id"] == "c1"
    assert kwargs["reviewed_by"] == "op1"


@patch("app.api.ai_review_routes.list_reviews")
def test_reviews_passes_search_params(mock_lr, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
    from app.core.config import get_settings

    get_settings.cache_clear()
    mock_lr.return_value = []
    from app.main import app

    client = TestClient(app)
    r = client.get(
        "/api/v1/internal/ai/reviews",
        params={"q": "x", "reviewed_by": "a", "scenario": "s"},
    )
    assert r.status_code == 200
    k = mock_lr.call_args.kwargs
    assert k["q"] == "x"
    assert k["reviewed_by"] == "a"
    assert k["scenario"] == "s"
