import pytest

from app.schemas.api import LegalClaimComposeRequest, LegalClaimReviewRequest
from app.services.business.rules import MIN_CLAIM_TEXT_LEN, validate_claim_compose_input, validate_claim_review_input
from app.services.gruzpotok_flow import legal_claim_compose, legal_claim_review


@pytest.mark.asyncio
async def test_claim_review_short_text_no_llm():
    body = LegalClaimReviewRequest(claim_text="x" * (MIN_CLAIM_TEXT_LEN - 1))
    import httpx

    async with httpx.AsyncClient() as client:
        out = await legal_claim_review(client, body)
    assert out.llm_invoked is False
    assert out.missing_information
    assert out.persona == "legal"


@pytest.mark.asyncio
async def test_claim_review_requires_minimum_length_message():
    miss = validate_claim_review_input("short")
    assert miss and "коротк" in miss[0].lower()


@pytest.mark.asyncio
async def test_claim_compose_short_facts_no_llm():
    body = LegalClaimComposeRequest(facts="x" * (MIN_CLAIM_TEXT_LEN - 1))
    import httpx

    async with httpx.AsyncClient() as client:
        out = await legal_claim_compose(client, body)
    assert out.llm_invoked is False
    assert out.missing_facts
    assert out.persona == "legal"


def test_claim_compose_requires_minimum_length_message():
    miss = validate_claim_compose_input("short")
    assert miss and "коротк" in miss[0].lower()
