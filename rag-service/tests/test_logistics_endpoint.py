import pytest

from app.schemas.api import FreightRouteAdviceRequest
from app.services.gruzpotok_flow import freight_route_advice


@pytest.mark.asyncio
async def test_route_advice_validation_no_llm_when_empty_fields():
    import httpx

    body = FreightRouteAdviceRequest(route_request="", vehicle="")
    async with httpx.AsyncClient() as client:
        out = await freight_route_advice(client, body)
    assert out.llm_invoked is False
    assert out.missing_information
    assert out.persona == "logistics"
