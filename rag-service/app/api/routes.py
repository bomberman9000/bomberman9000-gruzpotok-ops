from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import Json, RealDictCursor

from app.core.config import settings
from app.db.pool import get_conn
from app.schemas.api import (
    ChunkMetadata,
    DocumentDetail,
    DocumentListItem,
    HealthResponse,
    LegacyAskBody,
    QueryRequest,
    QueryResponse,
    SeedResponse,
    StatsResponse,
)
from app.services.rag_executor import execute_rag_query, log_payload_for_query

logger = logging.getLogger(__name__)

router = APIRouter()


def _log_query(
    *,
    user_query: str,
    normalized_query: str,
    category: str | None,
    source_type: str | None,
    top_k: int,
    chunk_ids: list[int],
    model: str,
    answer: str,
    citations: list[dict],
    mode: str,
) -> None:
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO query_logs (
                    user_query, normalized_query, category_filter, source_type_filter,
                    top_k, retrieved_chunk_ids, model_name, final_answer, citations_json, mode
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_query,
                    normalized_query,
                    category,
                    source_type,
                    top_k,
                    chunk_ids,
                    model,
                    answer,
                    Json(citations),
                    mode,
                ),
            )
            cur.close()
    except Exception:
        logger.exception("query_logs insert failed")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    pg_ok = False
    docs = 0
    chunks = 0
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            pg_ok = True
            cur.execute("SELECT COUNT(*) FROM documents WHERE is_active = TRUE")
            docs = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM document_chunks c JOIN documents d ON d.id = c.document_id WHERE d.is_active = TRUE")
            chunks = cur.fetchone()[0]
            cur.close()
    except Exception:
        logger.exception("health postgres")

    redis_ok: bool | None = None
    if settings.redis_url:
        try:
            import redis

            r = redis.Redis.from_url(settings.redis_url, socket_timeout=2)
            redis_ok = bool(r.ping())
        except Exception:
            redis_ok = False

    ollama_ok = False
    try:
        import urllib.request

        urllib.request.urlopen(f"{settings.ollama_base_url}/api/tags", timeout=3)
        ollama_ok = True
    except Exception:
        pass

    status = "ok" if pg_ok and ollama_ok else "degraded"
    return HealthResponse(
        status=status,
        postgres=pg_ok,
        redis=redis_ok,
        ollama_reachable=ollama_ok,
        documents_active=docs,
        chunks_total=chunks,
        ollama_base_url=settings.ollama_base_url,
    )


@router.post("/query", response_model=QueryResponse)
async def post_query(body: QueryRequest) -> QueryResponse:
    tk = body.top_k or settings.rag_top_k
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            res = await execute_rag_query(
                client,
                query=body.query,
                mode=body.mode,
                category=body.category,
                source_type=body.source_type,
                persona=body.persona,
                top_k=body.top_k,
                final_k=body.final_k,
                debug=body.debug,
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    citations_data = log_payload_for_query(res.rows)
    _log_query(
        user_query=body.query,
        normalized_query=res.normalized_query,
        category=body.category,
        source_type=body.source_type,
        top_k=tk,
        chunk_ids=[int(r["chunk_id"]) for r in res.rows],
        model=res.model,
        answer=res.answer,
        citations=citations_data,
        mode=res.mode,
    )

    return QueryResponse(
        answer=res.answer,
        citations=res.citations,
        retrieval_debug=res.retrieval_debug,
        model=res.model,
        mode=res.mode,
        llm_invoked=res.llm_invoked,
        persona=res.persona,
    )


@router.post("/seed", response_model=SeedResponse)
def post_seed() -> SeedResponse:
    from app.services.ingestion.runner import run_ingestion

    try:
        r = run_ingestion()
    except Exception as e:
        logger.exception("seed failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
    return SeedResponse(
        ingestion_run_id=r["ingestion_run_id"],
        status=r["status"],
        files_seen=r["files_seen"],
        files_indexed=r["files_indexed"],
        files_skipped=r["files_skipped"],
        documents_deactivated=int(r.get("documents_deactivated") or 0),
        errors=r.get("errors") or [],
    )


@router.get("/documents", response_model=list[DocumentListItem])
def list_documents(
    active_only: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[DocumentListItem]:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        q = """
            SELECT d.id, d.source_path, d.file_name, d.category, d.source_type, d.title,
                   d.checksum, d.imported_at::text, d.is_active,
                   (SELECT COUNT(*) FROM document_chunks c WHERE c.document_id = d.id) AS chunk_count
            FROM documents d
        """
        if active_only:
            q += " WHERE d.is_active = TRUE"
        q += " ORDER BY d.imported_at DESC NULLS LAST LIMIT %s"
        cur.execute(q, (limit,))
        rows = cur.fetchall()
        cur.close()
    out: list[DocumentListItem] = []
    for r in rows:
        out.append(
            DocumentListItem(
                id=str(r["id"]),
                source_path=r["source_path"],
                file_name=r["file_name"],
                category=r["category"],
                source_type=r["source_type"],
                title=r["title"],
                checksum=r["checksum"],
                imported_at=r["imported_at"],
                is_active=r["is_active"],
                chunk_count=r["chunk_count"],
            )
        )
    return out


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: UUID) -> DocumentDetail:
    uid = str(doc_id)
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT id, source_path, file_name, category, source_type, title, checksum,
                   last_updated_at::text, imported_at::text, version_tag, is_active, metadata_json
            FROM documents WHERE id = %s::uuid
            """,
            (uid,),
        )
        r = cur.fetchone()
        if not r:
            cur.close()
            raise HTTPException(status_code=404, detail="document not found")
        cur.execute(
            """
            SELECT id, chunk_index, token_count, section_title, article_ref, page_ref, chunk_text
            FROM document_chunks
            WHERE document_id = %s::uuid
            ORDER BY chunk_index ASC
            """,
            (uid,),
        )
        chunk_rows = cur.fetchall()
        cur.close()
    meta = r["metadata_json"]
    if isinstance(meta, str):
        meta = json.loads(meta)
    chunks_out: list[ChunkMetadata] = []
    for cr in chunk_rows:
        ct = cr.get("chunk_text") or ""
        excerpt = ct[:400] + ("…" if len(ct) > 400 else "")
        chunks_out.append(
            ChunkMetadata(
                id=int(cr["id"]),
                chunk_index=int(cr["chunk_index"]),
                token_count=cr.get("token_count"),
                section_title=cr.get("section_title"),
                article_ref=cr.get("article_ref"),
                page_ref=cr.get("page_ref"),
                excerpt=excerpt,
            )
        )
    return DocumentDetail(
        id=str(r["id"]),
        source_path=r["source_path"],
        file_name=r["file_name"],
        category=r["category"],
        source_type=r["source_type"],
        title=r["title"],
        checksum=r["checksum"],
        last_updated_at=r["last_updated_at"],
        imported_at=r["imported_at"],
        version_tag=r["version_tag"],
        is_active=r["is_active"],
        metadata_json=meta or {},
        chunks=chunks_out,
    )


@router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM documents WHERE is_active = TRUE")
        active_n = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM documents WHERE is_active = FALSE")
        inactive_n = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(*) FROM document_chunks c
            JOIN documents d ON d.id = c.document_id WHERE d.is_active = TRUE
            """
        )
        ch_n = cur.fetchone()[0]
        cur.execute(
            """
            SELECT category, COUNT(*) FROM documents WHERE is_active = TRUE GROUP BY category
            """
        )
        by_cat = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(
            """
            SELECT source_type, COUNT(*) FROM documents WHERE is_active = TRUE GROUP BY source_type
            """
        )
        by_st = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute(
            """
            SELECT status, finished_at::text
            FROM ingestion_runs ORDER BY id DESC LIMIT 1
            """
        )
        last_row = cur.fetchone()
        last_status = last_row[0] if last_row else None
        last_finished = last_row[1] if last_row else None
        cur.execute(
            """
            SELECT id, started_at::text, finished_at::text, status, files_seen, files_indexed, files_skipped
            FROM ingestion_runs ORDER BY id DESC LIMIT 5
            """
        )
        runs = [
            {
                "id": row[0],
                "started_at": row[1],
                "finished_at": row[2],
                "status": row[3],
                "files_seen": row[4],
                "files_indexed": row[5],
                "files_skipped": row[6],
            }
            for row in cur.fetchall()
        ]
        cur.close()
    return StatsResponse(
        active_documents_count=active_n,
        inactive_documents_count=inactive_n,
        chunks_count=ch_n,
        documents_by_category=by_cat,
        documents_by_source_type=by_st,
        last_ingestion_status=last_status,
        last_ingestion_finished_at=last_finished,
        documents_total=active_n,
        chunks_total=ch_n,
        last_ingestion_runs=runs,
    )


@router.post("/ask")
async def legacy_ask(body: LegacyAskBody) -> dict[str, Any]:
    """Обратная совместимость: старый формат { question, category } -> /query."""
    req = QueryRequest(
        query=body.question,
        mode=settings.rag_mode_default,
        persona=None,
        category=body.category if body.category in ("legal", "freight", "general") else None,
        source_type=None,
        top_k=None,
        final_k=None,
        debug=False,
    )
    res = await post_query(req)
    return {
        "answer": res.answer,
        "sources": [c.model_dump() for c in res.citations],
        "model": res.model,
        "llm_invoked": res.llm_invoked,
        "note": "deprecated: используйте POST /query",
    }
