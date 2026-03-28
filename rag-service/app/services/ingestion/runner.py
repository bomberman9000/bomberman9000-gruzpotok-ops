from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json

from app.core.config import settings
from app.services.ingestion.chunking import split_into_chunks
from app.services.ingestion.classify import category_from_relative_path, source_type_from_path
from app.services.ingestion.loaders import load_file_text

logger = logging.getLogger(__name__)

GLOB_PATTERNS = ("**/*.md", "**/*.txt", "**/*.json", "**/*.csv")

# Демо-файлы из examples/freight засоряют retrieval по ставкам (нет тарифов, общие правила).
# Юридические и general-примеры остаются в индексе для smoke-тестов README.
_EXCLUDED_REL_PREFIXES = ("examples/freight/",)


def should_index_relative_knowledge_path(rel_posix: str) -> bool:
    return not any(rel_posix.startswith(p) for p in _EXCLUDED_REL_PREFIXES)


def deactivate_excluded_source_documents(cur) -> int:
    """
    Документы по путям, которые больше не индексируются, должны стать неактивными —
    иначе старые чанки (например examples/freight/*.md) остаются в vector search.
    """
    total = 0
    for prefix in _EXCLUDED_REL_PREFIXES:
        pattern = prefix + "%"
        cur.execute(
            """
            UPDATE documents
            SET is_active = FALSE
            WHERE is_active = TRUE AND source_path LIKE %s
            """,
            (pattern,),
        )
        total += cur.rowcount
    return total


def _embed_sync(client: httpx.Client, text: str) -> list[float]:
    r = client.post(
        f"{settings.ollama_base_url}/api/embeddings",
        json={"model": settings.embedding_model, "prompt": text},
        timeout=180.0,
    )
    r.raise_for_status()
    emb = r.json().get("embedding")
    dim = settings.embedding_dimensions
    if not emb or len(emb) != dim:
        raise RuntimeError(f"Embedding dim mismatch: expected {dim}, got {len(emb) if emb else 0}")
    return emb


def _file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _guess_title(text: str, stem: str) -> str:
    for line in text.splitlines()[:40]:
        line = line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()[:500]
    return stem[:500]


def run_ingestion(knowledge_dir: Path | None = None) -> dict:
    root = Path(knowledge_dir or settings.knowledge_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Knowledge directory not found: {root}")

    conn = psycopg2.connect(settings.postgres_dsn)
    register_vector(conn)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO ingestion_runs (status, files_seen, files_indexed, files_skipped)
        VALUES ('running', 0, 0, 0)
        RETURNING id
        """
    )
    run_id = cur.fetchone()[0]
    conn.commit()

    deactivated = deactivate_excluded_source_documents(cur)
    conn.commit()

    files_seen = 0
    files_indexed = 0
    files_skipped = 0
    errors: list[str] = []

    paths: list[Path] = []
    for pattern in GLOB_PATTERNS:
        paths.extend(sorted(root.glob(pattern)))
    paths = sorted(set(paths))
    paths = [
        p
        for p in paths
        if should_index_relative_knowledge_path(p.relative_to(root).as_posix())
    ]

    try:
        with httpx.Client(timeout=300.0) as http:
            for path in paths:
                files_seen += 1
                rel = path.relative_to(root)
                rel_posix = rel.as_posix()
                try:
                    text = load_file_text(path)
                except (ValueError, OSError) as e:
                    errors.append(f"{rel_posix}: {e}")
                    continue

                checksum = _file_checksum(path)
                category = category_from_relative_path(rel)
                source_type = source_type_from_path(rel)
                title = _guess_title(text, path.stem)
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)

                cur.execute(
                    """
                    SELECT id, checksum FROM documents
                    WHERE source_path = %s AND is_active = TRUE
                    LIMIT 1
                    """,
                    (rel_posix,),
                )
                row = cur.fetchone()
                if row and row[1] == checksum:
                    files_skipped += 1
                    logger.info("skip unchanged %s", rel_posix)
                    conn.commit()
                    continue

                if row:
                    cur.execute(
                        "UPDATE documents SET is_active = FALSE WHERE id = %s::uuid",
                        (row[0],),
                    )

                cur.execute(
                    """
                    INSERT INTO documents (
                        source_path, file_name, category, source_type, title,
                        checksum, last_updated_at, imported_at, version_tag,
                        is_active, metadata_json
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, NOW(), %s, TRUE, %s
                    ) RETURNING id
                    """,
                    (
                        rel_posix,
                        path.name,
                        category,
                        source_type,
                        title,
                        checksum,
                        mtime,
                        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
                        Json(
                            {
                                "size_bytes": path.stat().st_size,
                                "indexed_at": datetime.now(UTC).isoformat(),
                            }
                        ),
                    ),
                )
                doc_id = cur.fetchone()[0]

                chunks = split_into_chunks(
                    text,
                    max_chars=1400,
                    overlap=200,
                    path_hint=rel_posix,
                )
                if not chunks:
                    cur.execute("DELETE FROM documents WHERE id = %s::uuid", (doc_id,))
                    errors.append(f"{rel_posix}: пустой текст после нарезки")
                    conn.commit()
                    continue
                for idx, ch in enumerate(chunks):
                    emb = _embed_sync(http, ch.text)
                    tok = max(1, int(len(ch.text.split()) * 1.3))
                    cur.execute(
                        """
                        INSERT INTO document_chunks (
                            document_id, chunk_index, chunk_text, embedding,
                            token_count, section_title, article_ref, page_ref,
                            metadata_json
                        ) VALUES (
                            %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            doc_id,
                            idx,
                            ch.text,
                            emb,
                            tok,
                            ch.section_title,
                            ch.article_ref,
                            None,
                            Json({}),
                        ),
                    )
                files_indexed += 1
                conn.commit()
                logger.info("indexed %s chunks=%s", rel_posix, len(chunks))

        status = "completed"
    except Exception as e:
        logger.exception("ingestion failed")
        status = "failed"
        errors.append(str(e))

    cur.execute(
        """
        UPDATE ingestion_runs SET
            finished_at = NOW(),
            status = %s,
            files_seen = %s,
            files_indexed = %s,
            files_skipped = %s,
            error_log = %s
        WHERE id = %s
        """,
        (
            status,
            files_seen,
            files_indexed,
            files_skipped,
            "\n".join(errors) if errors else None,
            run_id,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()

    return {
        "ingestion_run_id": run_id,
        "status": status,
        "files_seen": files_seen,
        "files_indexed": files_indexed,
        "files_skipped": files_skipped,
        "documents_deactivated": deactivated,
        "errors": errors,
    }
