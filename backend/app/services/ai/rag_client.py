from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Callable

import httpx

from app.core.config import Settings, get_settings
from app.services.ai import normalization as norm

logger = logging.getLogger(__name__)


class RagCallError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class RagApiClient:
    """Async HTTP-клиент к rag-api с retry и request id."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._s = settings or get_settings()
        self._base = self._s.rag_api_base_url.rstrip("/")
        self._timeout = httpx.Timeout(self._s.rag_api_timeout_sec)
        self._retries = self._s.rag_api_retry_count

    def _headers(self, request_id: str | None) -> dict[str, str]:
        rid = request_id or str(uuid.uuid4())
        return {
            "X-Request-ID": rid,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _post_json(
        self,
        path: str,
        body: dict[str, Any],
        *,
        request_id: str | None,
        endpoint_label: str,
    ) -> tuple[dict[str, Any], str, int]:
        """Возвращает (json dict, request_id, latency_ms)."""
        rid = request_id or str(uuid.uuid4())
        url = f"{self._base}{path}"
        last_err: Exception | None = None
        t0 = time.perf_counter()
        for attempt in range(self._retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    r = await client.post(url, json=body, headers=self._headers(rid))
                latency_ms = int((time.perf_counter() - t0) * 1000)
                text = r.text
                if r.status_code >= 500:
                    last_err = RagCallError(f"rag-api {r.status_code}: {text[:500]}", retryable=True)
                    await asyncio.sleep(0.3 * (attempt + 1))
                    continue
                if r.status_code >= 400:
                    raise RagCallError(f"rag-api {r.status_code}: {text[:800]}", retryable=False)
                try:
                    parsed = r.json()
                except json.JSONDecodeError as e:
                    raise RagCallError(f"invalid JSON from rag-api: {e}", retryable=False) from e
                if not isinstance(parsed, dict):
                    raise RagCallError("rag-api JSON is not an object", retryable=False)
                logger.info(
                    "rag_call_ok endpoint=%s request_id=%s latency_ms=%s status=%s",
                    endpoint_label,
                    rid,
                    latency_ms,
                    r.status_code,
                )
                return parsed, rid, latency_ms
            except httpx.TimeoutException as e:
                last_err = RagCallError(f"timeout: {e}", retryable=True)
                await asyncio.sleep(0.4 * (attempt + 1))
            except httpx.RequestError as e:
                last_err = RagCallError(f"network: {e}", retryable=True)
                await asyncio.sleep(0.4 * (attempt + 1))
        assert last_err is not None
        raise last_err

    async def query(
        self,
        *,
        query: str,
        mode: str | None = None,
        persona: str | None = None,
        category: str | None = None,
        source_type: str | None = None,
        debug: bool | None = None,
        request_id: str | None = None,
    ) -> tuple[dict[str, Any], str, int]:
        dbg = self._s.rag_api_debug_default if debug is None else debug
        body: dict[str, Any] = {"query": query, "debug": dbg}
        if mode is not None:
            body["mode"] = mode
        if persona is not None:
            body["persona"] = persona
        if category is not None:
            body["category"] = category
        if source_type is not None:
            body["source_type"] = source_type
        return await self._post_json("/query", body, request_id=request_id, endpoint_label="query")

    async def claim_review(
        self,
        *,
        claim_text: str,
        contract_context: str = "",
        counterparty: str = "",
        debug: bool | None = None,
        request_id: str | None = None,
    ) -> tuple[dict[str, Any], str, int]:
        dbg = self._s.rag_api_debug_default if debug is None else debug
        body = {
            "claim_text": claim_text,
            "contract_context": contract_context,
            "counterparty": counterparty,
            "debug": dbg,
        }
        return await self._post_json("/legal/claim-review", body, request_id=request_id, endpoint_label="claim_review")

    async def claim_draft(
        self,
        *,
        claim_text: str,
        company_name: str = "",
        signer: str = "",
        request_id: str | None = None,
    ) -> tuple[dict[str, Any], str, int]:
        body = {
            "claim_text": claim_text,
            "company_name": company_name,
            "signer": signer,
            "mode": "draft",
        }
        return await self._post_json("/legal/claim-draft", body, request_id=request_id, endpoint_label="claim_draft")

    async def risk_check(
        self,
        *,
        situation: str,
        counterparty_info: str = "",
        route: str = "",
        debug: bool | None = None,
        request_id: str | None = None,
    ) -> tuple[dict[str, Any], str, int]:
        dbg = self._s.rag_api_debug_default if debug is None else debug
        body = {
            "situation": situation,
            "counterparty_info": counterparty_info,
            "route": route,
            "debug": dbg,
        }
        return await self._post_json("/freight/risk-check", body, request_id=request_id, endpoint_label="risk_check")

    async def route_advice(
        self,
        *,
        route_request: str,
        vehicle: str,
        cargo: str = "",
        constraints: str = "",
        request_id: str | None = None,
    ) -> tuple[dict[str, Any], str, int]:
        body = {
            "route_request": route_request,
            "vehicle": vehicle,
            "cargo": cargo,
            "constraints": constraints,
        }
        return await self._post_json("/freight/route-advice", body, request_id=request_id, endpoint_label="route_advice")

    async def document_check(
        self,
        *,
        document_text: str,
        document_type: str = "",
        debug: bool | None = None,
        request_id: str | None = None,
    ) -> tuple[dict[str, Any], str, int]:
        dbg = self._s.rag_api_debug_default if debug is None else debug
        body = {"document_text": document_text, "document_type": document_type, "debug": dbg}
        return await self._post_json(
            "/freight/document-check",
            body,
            request_id=request_id,
            endpoint_label="document_check",
        )

    async def transport_order_compose(
        self,
        *,
        request_text: str,
        debug: bool | None = None,
        request_id: str | None = None,
    ) -> tuple[dict[str, Any], str, int]:
        dbg = self._s.rag_api_debug_default if debug is None else debug
        body = {"request_text": request_text, "debug": dbg}
        return await self._post_json(
            "/freight/transport-order-compose",
            body,
            request_id=request_id,
            endpoint_label="transport_order_compose",
        )

    async def transport_order_pdf(
        self,
        *,
        body: dict[str, Any],
        request_id: str | None = None,
    ) -> tuple[bytes, str, int]:
        """POST JSON → бинарный PDF (не JSON)."""
        rid = request_id or str(uuid.uuid4())
        url = f"{self._base}/freight/transport-order-pdf"
        headers = {
            "X-Request-ID": rid,
            "Content-Type": "application/json",
        }
        t0 = time.perf_counter()
        last_err: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    r = await client.post(url, json=body, headers=headers)
                latency_ms = int((time.perf_counter() - t0) * 1000)
                if r.status_code >= 500:
                    last_err = RagCallError(f"rag-api {r.status_code}: {r.text[:500]}", retryable=True)
                    await asyncio.sleep(0.3 * (attempt + 1))
                    continue
                if r.status_code >= 400:
                    raise RagCallError(f"rag-api {r.status_code}: {r.text[:800]}", retryable=False)
                ct = (r.headers.get("content-type") or "").lower()
                if "pdf" not in ct and r.content[:4] != b"%PDF":
                    raise RagCallError(
                        f"rag-api вернул не PDF (content-type={ct!r})",
                        retryable=False,
                    )
                logger.info(
                    "rag_call_ok endpoint=%s request_id=%s latency_ms=%s status=%s",
                    "transport_order_pdf",
                    rid,
                    latency_ms,
                    r.status_code,
                )
                return r.content, rid, latency_ms
            except httpx.TimeoutException as e:
                last_err = RagCallError(f"timeout: {e}", retryable=True)
                await asyncio.sleep(0.4 * (attempt + 1))
            except httpx.RequestError as e:
                last_err = RagCallError(f"network: {e}", retryable=True)
                await asyncio.sleep(0.4 * (attempt + 1))
        assert last_err is not None
        raise last_err


def normalize_raw(
    endpoint: str,
    raw: dict[str, Any],
) -> Any:
    m: dict[str, Callable[[dict[str, Any]], Any]] = {
        "query": norm.normalize_from_query,
        "claim_review": norm.normalize_from_claim_review,
        "claim_draft": norm.normalize_from_claim_draft,
        "risk_check": norm.normalize_from_risk_check,
        "route_advice": norm.normalize_from_route_advice,
        "document_check": norm.normalize_from_document_check,
        "transport_order_compose": norm.normalize_from_transport_order_compose,
    }
    fn = m.get(endpoint)
    if not fn:
        return norm.fallback_invalid_upstream(f"unknown endpoint {endpoint}")
    return fn(raw)
