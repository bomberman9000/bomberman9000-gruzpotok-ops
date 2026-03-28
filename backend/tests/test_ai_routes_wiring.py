import pytest

from app.services.ai.gateway import run_ai_gateway
from app.services.ai.rag_client import RagApiClient


@pytest.mark.asyncio
async def test_run_wraps_normalize_and_presentation():
    async def fake_call(client: RagApiClient):
        return (
            {
                "answer": "a",
                "citations": [
                    {
                        "document_id": "1",
                        "file_name": "f",
                        "source_path": "p",
                        "chunk_index": 0,
                        "chunk_id": 1,
                        "excerpt": "e",
                    }
                ],
                "model": "m",
                "mode": "balanced",
                "llm_invoked": True,
            },
            "rid-x",
            3,
        )

    env = await run_ai_gateway(
        endpoint="query",
        rag_path="/query",
        request_id="req-1",
        user_input={"kind": "query"},
        call=fake_call,
    )
    assert env.meta.request_id == "rid-x"
    assert env.meta.llm_invoked is True
    assert env.data.presentation is not None
    assert env.data.presentation.short_summary
    assert env.data.presentation.title
    assert env.data.presentation.actions
