from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from app.core.config import get_settings
from app.schemas.unified import AIEnvelope, AIMeta, UnifiedAIResponse
from app.services.ai import normalization as norm
from app.services.ai.ai_call_service import record_ai_call
from app.services.presentation.core import attach_presentation
from app.services.presentation.entity_context import context_from_gateway
from app.services.ai.rag_client import RagApiClient, RagCallError, normalize_raw

logger = logging.getLogger(__name__)


def build_meta(
    *,
    endpoint: str,
    request_id: str,
    latency_ms: int,
    rag_path: str,
    data: UnifiedAIResponse,
    user_input: dict | None,
) -> AIMeta:
    ctx = context_from_gateway(endpoint=endpoint, user_input=user_input, request_id=request_id)
    return AIMeta(
        request_id=request_id,
        endpoint=endpoint,
        latency_ms=latency_ms,
        citations_count=len(data.citations or []),
        rag_path=rag_path,
        persona=data.persona,
        mode=data.mode,
        llm_invoked=data.llm_invoked,
        entity_type=ctx.entity_type,
        entity_id=ctx.entity_id,
        scenario=ctx.scenario,
        screen_hint=ctx.screen_hint,
    )


async def run_ai_gateway(
    *,
    endpoint: str,
    rag_path: str,
    request_id: str,
    user_input: dict | None,
    call: Callable[[RagApiClient], Awaitable[tuple[dict, str, int]]],
) -> AIEnvelope:
    """Единая точка: rag → нормализация → presentation → persistence."""
    s = get_settings()
    ui = dict(user_input or {})
    t_wall = time.perf_counter()

    def persist(envelope: AIEnvelope, *, rag_reachable: bool, rag_error: str | None) -> None:
        wall_ms = int((time.perf_counter() - t_wall) * 1000)
        lat = envelope.meta.latency_ms if envelope.meta.latency_ms else wall_ms
        record_ai_call(
            request_id=envelope.meta.request_id,
            endpoint=endpoint,
            meta=envelope.meta,
            data=envelope.data,
            user_input=ui,
            latency_ms=lat,
            rag_reachable=rag_reachable,
            rag_error=rag_error,
        )

    if not s.rag_api_enabled:
        data = norm.fallback_disabled()
        attach_presentation(data, endpoint=endpoint, request_id=request_id, user_input=ui)
        envelope = AIEnvelope(
            meta=build_meta(
                endpoint=endpoint,
                request_id=request_id,
                latency_ms=0,
                rag_path=rag_path,
                data=data,
                user_input=ui,
            ),
            data=data,
        )
        persist(envelope, rag_reachable=True, rag_error=None)
        return envelope

    t0 = time.perf_counter()
    client = RagApiClient(s)
    try:
        raw, rid, lm = await call(client)
        data = normalize_raw(endpoint, raw)
        attach_presentation(data, endpoint=endpoint, request_id=rid, user_input=ui)
        envelope = AIEnvelope(
            meta=build_meta(
                endpoint=endpoint,
                request_id=rid,
                latency_ms=lm,
                rag_path=rag_path,
                data=data,
                user_input=ui,
            ),
            data=data,
        )
        persist(envelope, rag_reachable=True, rag_error=None)
        return envelope
    except RagCallError as e:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        logger.warning(
            "rag_call_failed endpoint=%s request_id=%s err=%s retryable=%s",
            endpoint,
            request_id,
            str(e)[:500],
            e.retryable,
        )
        fb = norm.fallback_unavailable(
            reason=str(e),
            user_message="Сервис знаний временно недоступен. Попробуйте позже.",
            retryable=e.retryable,
        )
        attach_presentation(fb, endpoint=endpoint, request_id=request_id, user_input=ui)
        envelope = AIEnvelope(
            meta=build_meta(
                endpoint=endpoint,
                request_id=request_id,
                latency_ms=latency_ms,
                rag_path=rag_path,
                data=fb,
                user_input=ui,
            ),
            data=fb,
        )
        persist(envelope, rag_reachable=False, rag_error=str(e)[:2000])
        return envelope
