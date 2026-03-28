import pytest

from app.schemas.api import FreightRiskCheckRequest
from app.services.gruzpotok_flow import freight_risk_check


@pytest.mark.asyncio
async def test_risk_check_insufficient_returns_structured_without_llm(monkeypatch):
    from app.services import gruzpotok_flow as gf
    from app.services.rag_executor import RagExecuteResult
    from app.utils.citations import citations_from_chunks

    async def fake_exec(*args, **kwargs):
        return RagExecuteResult(
            answer="no data",
            citations=citations_from_chunks([]),
            rows=[],
            normalized_query="nq",
            llm_invoked=False,
            retrieval_debug=None,
            model="m",
            mode="strict",
            persona="antifraud",
            prompt_template_used="antifraud",
            applied_filters={},
            insufficient_data=True,
        )

    monkeypatch.setattr(gf, "execute_rag_query", fake_exec)

    import httpx

    body = FreightRiskCheckRequest(situation="test situation " * 5)
    async with httpx.AsyncClient() as client:
        out = await freight_risk_check(client, body)
    assert out.llm_invoked is False
    assert out.persona == "antifraud"
    assert out.red_flags
