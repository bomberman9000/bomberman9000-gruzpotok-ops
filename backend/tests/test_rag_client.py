import os

import pytest

from app.core.config import get_settings
from app.services.ai.rag_client import RagApiClient, RagCallError


@pytest.fixture(autouse=True)
def clear_settings_cache():
    os.environ.setdefault("RAG_API_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_query_success_monkeypatch(monkeypatch):
    async def fake_post_json(self, path, body, *, request_id, endpoint_label):
        return (
            {
                "answer": "ok",
                "citations": [],
                "model": "m",
                "mode": "balanced",
                "llm_invoked": True,
            },
            "rid-1",
            12,
        )

    monkeypatch.setattr(RagApiClient, "_post_json", fake_post_json)
    c = RagApiClient()
    raw, rid, lm = await c.query(query="test", request_id="abc")
    assert raw["answer"] == "ok"
    assert rid == "rid-1"
    assert lm == 12


@pytest.mark.asyncio
async def test_timeout_fallback_raises_retryable(monkeypatch):
    async def boom(self, path, body, *, request_id, endpoint_label):
        raise RagCallError("timeout", retryable=True)

    monkeypatch.setattr(RagApiClient, "_post_json", boom)
    c = RagApiClient()
    with pytest.raises(RagCallError) as e:
        await c.query(query="x")
    assert e.value.retryable is True


def test_disabled_path_returns_envelope():
    os.environ["RAG_API_ENABLED"] = "0"
    get_settings.cache_clear()
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    r = client.post("/api/v1/ai/query", json={"query": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["status"] == "disabled"
    os.environ["RAG_API_ENABLED"] = "true"
    get_settings.cache_clear()
