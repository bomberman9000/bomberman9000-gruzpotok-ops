from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from app.services.document_pipeline import (
    DocumentPipelineError,
    detect_document_type,
    extract_text_from_document,
)


@dataclass(frozen=True)
class DocumentCapableInputPolicy:
    route_label: str
    field_name: str
    max_file_mb: int = 15
    max_pages: int = 200


class DocumentInputRouteError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


DOCUMENT_CAPABLE_INPUTS: dict[str, DocumentCapableInputPolicy] = {
    "legal_claim_review": DocumentCapableInputPolicy(
        route_label="legal_claim_review",
        field_name="claim_text",
    ),
    "legal_claim_draft": DocumentCapableInputPolicy(
        route_label="legal_claim_draft",
        field_name="claim_text",
    ),
    "legal_claim_compose": DocumentCapableInputPolicy(
        route_label="legal_claim_compose",
        field_name="facts",
    ),
    "freight_document_check": DocumentCapableInputPolicy(
        route_label="freight_document_check",
        field_name="document_text",
    ),
    "freight_transport_order_compose": DocumentCapableInputPolicy(
        route_label="freight_transport_order_compose",
        field_name="request_text",
    ),
}

INTENTIONALLY_PLAIN_TEXT_ONLY_ROUTES: tuple[str, ...] = (
    "freight_risk_check",
    "freight_route_advice",
    "query",
)

SUPPORTED_DOCUMENT_PATH_SUFFIXES = frozenset({".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png", ".webp"})
DEFAULT_DOCUMENT_INPUT_ROOT = "/tmp/rag-document-input"
DOCUMENT_INPUT_ROOT_ENV = "RAG_DOCUMENT_INPUT_ROOT"
DOCUMENT_DEBUG_PREVIEW_ENV = "RAG_DOCUMENT_DEBUG_PREVIEW"


def get_document_input_policy(route_label: str) -> DocumentCapableInputPolicy | None:
    return DOCUMENT_CAPABLE_INPUTS.get(route_label)


def looks_like_document_path(text: str) -> bool:
    if not text or "\n" in text or "\r" in text or len(text) > 500:
        return False
    suffix = Path(text).suffix.lower()
    return suffix in SUPPORTED_DOCUMENT_PATH_SUFFIXES


def document_input_root() -> Path:
    raw = (os.environ.get(DOCUMENT_INPUT_ROOT_ENV) or DEFAULT_DOCUMENT_INPUT_ROOT).strip()
    return Path(raw).resolve()


def document_debug_preview_enabled() -> bool:
    raw = (os.environ.get(DOCUMENT_DEBUG_PREVIEW_ENV) or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _short_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:12]


def _redacted_preview(text: str) -> str | None:
    if not document_debug_preview_enabled():
        return None
    return text[:300]


def _resolve_allowed_document_path(candidate: str) -> Path:
    root = document_input_root()
    raw_path = Path(candidate)
    candidate_path = raw_path if raw_path.is_absolute() else root / raw_path
    try:
        resolved = candidate_path.resolve(strict=True)
    except FileNotFoundError as e:
        raise DocumentInputRouteError("file_not_found", "Файл документа не найден в разрешённой директории.") from e

    if not resolved.is_relative_to(root):
        raise DocumentInputRouteError(
            "document_path_outside_root",
            "Путь к документу вне разрешённой директории RAG_DOCUMENT_INPUT_ROOT.",
        )
    if not resolved.is_file():
        raise DocumentInputRouteError("file_not_found", "Файл документа не найден в разрешённой директории.")
    return resolved


def map_document_error_code(message: str) -> str:
    lowered = message.lower()
    if "ocr backend unavailable" in lowered:
        return "ocr_backend_unavailable"
    if "ocr не извлёк текст" in lowered or "скан" in lowered:
        return "scan_without_ocr"
    if "битый" in lowered or "поврежд" in lowered or "нечитаем" in lowered:
        return "broken_document"
    if "empty extracted text" in lowered or "пуст" in lowered:
        return "empty_text"
    return "extraction_failed"


def resolve_document_capable_input(
    raw_input: str,
    *,
    route_label: str,
    logger: logging.Logger,
) -> tuple[str, dict[str, Any]]:
    policy = get_document_input_policy(route_label)
    if policy is None:
        raise ValueError(f"route is not document-capable: {route_label}")

    candidate = (raw_input or "").strip()
    info: dict[str, Any] = {
        "route_mode": "plain_text_direct",
        "source_path": None,
        "document_type": None,
        "field_name": policy.field_name,
        "extraction_method": None,
        "extraction_quality": None,
        "text_char_count": len(candidate),
        "input_sha256_12": _short_sha256(candidate),
        "preview": _redacted_preview(candidate),
    }

    if not looks_like_document_path(candidate):
        logger.info(
            "document_input route=%s field=%s mode=plain_text text_char_count=%s input_sha256_12=%s preview_enabled=%s",
            route_label,
            policy.field_name,
            len(candidate),
            info["input_sha256_12"],
            document_debug_preview_enabled(),
        )
        return candidate, info

    path = _resolve_allowed_document_path(candidate)

    try:
        doc_type = detect_document_type(path)
    except DocumentPipelineError as e:
        raise DocumentInputRouteError("unsupported_type", str(e)) from e

    try:
        parsed = extract_text_from_document(
            path,
            max_file_mb=policy.max_file_mb,
            max_pages=policy.max_pages,
        )
    except DocumentPipelineError as e:
        code = getattr(e, "code", None) or map_document_error_code(str(e))
        logger.warning(
            "document_input_failed route=%s field=%s code=%s file_name=%s file_sha256_12=%s type=%s err=%s",
            route_label,
            policy.field_name,
            code,
            path.name,
            _short_sha256(str(path)),
            doc_type,
            str(e)[:500],
        )
        raise DocumentInputRouteError(code, str(e)) from e

    logger.info(
        "document_input route=%s field=%s mode=document_pipeline file_name=%s file_sha256_12=%s type=%s extraction_method=%s extraction_quality=%s text_char_count=%s preview_enabled=%s",
        route_label,
        policy.field_name,
        path.name,
        _short_sha256(str(path)),
        doc_type,
        parsed.extraction_method,
        parsed.extraction_quality,
        parsed.text_char_count,
        document_debug_preview_enabled(),
    )
    info.update(
        {
            "route_mode": "document_pipeline_extract_then_rag",
            "source_path": str(path),
            "source_file_name": path.name,
            "source_path_sha256_12": _short_sha256(str(path)),
            "document_type": doc_type,
            "extraction_method": parsed.extraction_method,
            "extraction_quality": parsed.extraction_quality,
            "text_char_count": parsed.text_char_count,
            "preview": _redacted_preview(parsed.text),
        }
    )
    return parsed.text, info


def log_document_prompt_input(
    logger: logging.Logger,
    *,
    handler_name: str,
    task: str,
    source_info: dict[str, Any],
    input_text: str,
    prompt_text: str,
) -> None:
    logger.info(
        "%s prompt_input route=%s field=%s task=%s text_char_count=%s prompt_char_count=%s input_sha256_12=%s prompt_sha256_12=%s preview_enabled=%s",
        handler_name,
        source_info.get("route_mode"),
        source_info.get("field_name"),
        task,
        len(input_text),
        len(prompt_text),
        _short_sha256(input_text or ""),
        _short_sha256(prompt_text or ""),
        document_debug_preview_enabled(),
    )
