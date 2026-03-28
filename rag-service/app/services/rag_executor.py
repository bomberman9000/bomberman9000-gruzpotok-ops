from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.core.config import settings
from app.schemas.api import CitationItem, RetrievalDebug
from app.services.generation.ollama_client import build_json_user_prompt, build_user_prompt, chat, embed_query
from app.services.personas.registry import (
    PersonaId,
    resolve_effective_filters,
    validate_filters_for_persona,
)
from app.services.retrieval.pipeline import retrieve_for_query, strict_retrieval_ok
from app.utils.citations import citations_from_chunks
from app.utils.logistics_sanitize import sanitize_logistics_answer


Mode = Literal["balanced", "strict", "draft"]


def effective_mode(
    *,
    mode: Mode | None,
    persona: PersonaId | None,
) -> Mode:
    if mode is not None:
        return mode
    if persona == "legal":
        return "strict"
    if persona == "logistics":
        return "balanced"
    if persona == "antifraud":
        return "strict"
    return settings.rag_mode_default


@dataclass
class RagExecuteResult:
    answer: str
    citations: list[CitationItem]
    rows: list[dict]
    normalized_query: str
    llm_invoked: bool
    retrieval_debug: RetrievalDebug | None
    model: str
    mode: Mode
    persona: PersonaId | None
    prompt_template_used: str | None
    applied_filters: dict[str, Any]
    insufficient_data: bool = False


def _citations_data_for_log(rows: list[dict]) -> list[dict]:
    return [
        {
            "document_id": str(r.get("document_id")),
            "file_name": r.get("file_name"),
            "chunk_index": r.get("chunk_index"),
            "rerank_score": r.get("rerank_score"),
            "dist": r.get("dist"),
        }
        for r in rows
    ]


async def execute_rag_query(
    client: httpx.AsyncClient,
    *,
    query: str,
    mode: Mode | None,
    category: str | None,
    source_type: str | None,
    persona: PersonaId | None,
    top_k: int | None,
    final_k: int | None,
    debug: bool,
    strict_min_chunks: int | None = None,
    json_schema: str | None = None,
) -> RagExecuteResult:
    validate_filters_for_persona(persona, category=category, source_type=source_type)
    eff_mode = effective_mode(mode=mode, persona=persona)
    cats, sts = resolve_effective_filters(persona, category=category, source_type=source_type)

    tk = top_k or settings.rag_top_k
    fk = final_k or settings.rag_final_k
    smc = strict_min_chunks if strict_min_chunks is not None else settings.strict_min_chunks

    emb = await embed_query(client, query.strip())
    rows, nq = retrieve_for_query(
        emb,
        query,
        top_k=tk,
        final_k=fk,
        categories=cats,
        source_types=sts,
        persona=persona,
    )

    prompt_template_used = persona
    applied_filters: dict[str, Any] = {
        "categories": cats,
        "source_types": sts,
    }

    def make_dbg() -> RetrievalDebug | None:
        if not debug:
            return None
        return RetrievalDebug(
            top_k=tk,
            final_k=fk,
            used_chunks=len(rows),
            normalized_query=nq,
            scores=[
                {
                    "chunk_id": r.get("chunk_id"),
                    "dist": float(r.get("dist", 0)),
                    "rerank_score": float(r.get("rerank_score", 0)),
                }
                for r in rows
            ],
            persona=persona,
            applied_filters=applied_filters,
            prompt_template_used=prompt_template_used,
        )

    strict_fail = (
        eff_mode == "strict"
        and (not strict_retrieval_ok(rows) or len(rows) < max(1, smc))
    )
    if strict_fail or (eff_mode == "strict" and not rows):
        msg = (
            "В локальной базе знаний недостаточно релевантных материалов для ответа "
            "в строгом режиме. Добавьте документы в каталог knowledge или уточните запрос."
        )
        return RagExecuteResult(
            answer=msg,
            citations=citations_from_chunks(rows) if rows else [],
            rows=rows,
            normalized_query=nq,
            llm_invoked=False,
            retrieval_debug=make_dbg(),
            model=settings.chat_model,
            mode=eff_mode,
            persona=persona,
            prompt_template_used=prompt_template_used,
            applied_filters=applied_filters,
            insufficient_data=True,
        )

    if not rows:
        msg = "В базе нет проиндексированных фрагментов. Выполните POST /seed или python -m app.seed."
        return RagExecuteResult(
            answer=msg,
            citations=[],
            rows=[],
            normalized_query=nq,
            llm_invoked=False,
            retrieval_debug=make_dbg(),
            model=settings.chat_model,
            mode=eff_mode,
            persona=persona,
            prompt_template_used=prompt_template_used,
            applied_filters=applied_filters,
            insufficient_data=True,
        )

    if json_schema:
        user_prompt = build_json_user_prompt(query, rows, json_schema)
    else:
        user_prompt = build_user_prompt(query, rows, mode=eff_mode)
    answer = await chat(client, user_prompt, mode=eff_mode, persona=persona)
    if persona == "logistics" and not json_schema:
        answer = sanitize_logistics_answer(answer, nq)
    cits = citations_from_chunks(rows)

    return RagExecuteResult(
        answer=answer,
        citations=cits,
        rows=rows,
        normalized_query=nq,
        llm_invoked=True,
        retrieval_debug=make_dbg(),
        model=settings.chat_model,
        mode=eff_mode,
        persona=persona,
        prompt_template_used=prompt_template_used,
        applied_filters=applied_filters,
        insufficient_data=False,
    )


def log_payload_for_query(rows: list[dict]) -> list[dict]:
    return _citations_data_for_log(rows)
