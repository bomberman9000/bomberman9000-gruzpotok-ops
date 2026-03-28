from unittest.mock import MagicMock, patch

import pytest

from app.core.config import get_settings
from app.services.ai.gateway import run_ai_gateway
from app.services.ai.rag_client import RagApiClient, RagCallError


def test_feedback_endpoint_without_db_returns_saved_false(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/api/v1/ai/feedback",
        json={
            "request_id": "req-12345",
            "useful": True,
            "correct": None,
            "comment": "ok",
            "user_role": "manager",
            "source_screen": "claim",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["saved"] is False


def test_internal_claim_review_path_exists(monkeypatch):
    monkeypatch.setenv("RAG_API_ENABLED", "0")
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/api/v1/internal/claims/demo-claim-1/ai-review",
        json={"claim_text": "long text " * 5, "contract_context": "", "counterparty": "X"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["status"] == "disabled"
    assert body["meta"]["request_id"]


def test_request_id_propagates_to_meta(monkeypatch):
    monkeypatch.setenv("RAG_API_ENABLED", "0")
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.post(
        "/api/v1/ai/query",
        headers={"X-Request-ID": "propagate-me"},
        json={"query": "hello world test"},
    )
    assert r.status_code == 200
    assert r.json()["meta"]["request_id"] == "propagate-me"


@pytest.mark.asyncio
async def test_fallback_persists_with_unavailable(monkeypatch):
    monkeypatch.setenv("RAG_API_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    captured: dict = {}

    def capture(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("app.services.ai.gateway.record_ai_call", capture)

    async def boom(c: RagApiClient):
        raise RagCallError("timeout", retryable=True)

    env = await run_ai_gateway(
        endpoint="query",
        rag_path="/query",
        request_id="req-prop",
        user_input={"x": 1},
        call=boom,
    )
    assert env.data.status == "unavailable"
    assert captured.get("request_id") == "req-prop"
    assert captured.get("rag_reachable") is False
    assert captured.get("rag_error")


@patch("app.services.ai.ai_call_service.get_settings")
def test_record_ai_call_observability(gs):
    gs.return_value = MagicMock(database_url=None)
    from app.services.observability import reset_for_tests, snapshot

    reset_for_tests()
    from app.services.ai.ai_call_service import record_ai_call
    from app.schemas.unified import AIMeta, UnifiedAIResponse

    data = UnifiedAIResponse(status="ok", answer="x", llm_invoked=True)
    meta = AIMeta(
        request_id="r1",
        endpoint="query",
        latency_ms=10,
        citations_count=0,
        rag_path="/query",
    )
    record_ai_call(
        request_id="r1",
        endpoint="query",
        meta=meta,
        data=data,
        user_input={"q": "1"},
        latency_ms=10,
        rag_reachable=True,
        rag_error=None,
    )
    snap = snapshot()
    assert snap["total_ai_calls"] == 1
