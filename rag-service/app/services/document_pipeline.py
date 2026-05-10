from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from xml.etree import ElementTree as ET

import httpx
from PIL import Image
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services import pdf_pipeline as pdf
from app.services.generation.ollama_client import chat_raw
from app.core.config import settings


DocumentType = Literal["pdf", "docx", "txt", "image"]
DocumentTask = pdf.PdfTask
ClaimReplyMode = pdf.ClaimReplyMode

SUPPORTED_DOCUMENT_TYPES: tuple[DocumentType, ...] = ("pdf", "docx", "txt", "image")
SUPPORTED_DOCUMENT_TASKS = pdf.SUPPORTED_PDF_TASKS
SUPPORTED_CLAIM_REPLY_MODES = pdf.SUPPORTED_CLAIM_REPLY_MODES
DEFAULT_MAX_FILE_MB = pdf.DEFAULT_MAX_FILE_MB
DEFAULT_MAX_PAGES = pdf.DEFAULT_MAX_PAGES
DEFAULT_CHUNK_MAX_CHARS = pdf.DEFAULT_CHUNK_MAX_CHARS
DEFAULT_CHUNK_OVERLAP = pdf.DEFAULT_CHUNK_OVERLAP
DEFAULT_DIRECT_TEXT_LIMIT = pdf.DEFAULT_DIRECT_TEXT_LIMIT

DocumentPipelineError = pdf.PdfDocumentError

_WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class ParsedDocumentBlock:
    index: int
    text: str
    page_number: int | None = None
    kind: str = "block"


@dataclass(frozen=True)
class ParsedDocument:
    source_path: str
    file_type: DocumentType
    file_size_bytes: int
    text: str
    blocks: list[ParsedDocumentBlock]
    warnings: list[str]
    extraction_method: str
    page_count: int
    extraction_quality: Literal["high", "medium", "low"] = "high"
    quality_reasons: list[str] = field(default_factory=list)
    text_char_count: int = 0
    non_whitespace_char_count: int = 0
    suspicious_text: bool = False
    ocr_used: bool = False
    extraction_status: str = "text_extracted"
    text_layer_found: bool | None = None
    pages_present: bool = True
    fallback_used: Literal["none", "ocr", "vision", "tech_notice"] = "none"
    user_safe_reason: str | None = None

    @property
    def pages(self) -> list[ParsedDocumentBlock]:
        return self.blocks


@dataclass(frozen=True)
class DocumentAnalysisResult:
    task: DocumentTask
    run_id: str
    created_at_utc: str
    source_file_name: str
    source_file_hash_sha256: str
    model_used: str
    source_path: str
    file_type: DocumentType
    extraction_method: str
    extraction_quality: Literal["high", "medium", "low"]
    quality_reasons: list[str]
    text_char_count: int
    non_whitespace_char_count: int
    suspicious_text: bool
    ocr_used: bool
    extraction_status: str
    text_layer_found: bool | None
    pages_present: bool
    fallback_used: str
    user_safe_reason: str | None
    text_path: str
    analysis_path: str
    page_count: int
    block_count: int
    chunk_count: int
    summary: str
    extracted_facts: dict[str, object]
    draft_reply: str
    warnings: list[str]
    raw_response: dict[str, object]
    reply_mode_requested: str | None = None
    reply_mode_effective: str | None = None


def detect_document_type(path: str | Path) -> DocumentType:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    if suffix == ".txt":
        return "txt"
    if suffix in _IMAGE_SUFFIXES:
        return "image"
    raise DocumentPipelineError(f"unsupported document type: {Path(path).name}")


def extract_text_from_document(
    path: str | Path,
    *,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
    max_pages: int = DEFAULT_MAX_PAGES,
    enable_ocr_fallback: bool = False,
) -> ParsedDocument:
    doc_type = detect_document_type(path)
    if doc_type == "pdf":
        return extract_text_from_pdf(
            path,
            max_file_mb=max_file_mb,
            max_pages=max_pages,
            ocr_fallback=enable_ocr_fallback,
        )
    if doc_type == "docx":
        return extract_text_from_docx(path, max_file_mb=max_file_mb)
    if doc_type == "txt":
        return extract_text_from_txt(path, max_file_mb=max_file_mb)
    return extract_text_from_image(path, max_file_mb=max_file_mb)


def assess_extraction_quality(parsed: ParsedDocument) -> ParsedDocument:
    text = parsed.text or ""
    text_char_count = len(text)
    non_whitespace = sum(1 for ch in text if not ch.isspace())
    alnum_count = sum(1 for ch in text if ch.isalnum())
    alpha_count = sum(1 for ch in text if ch.isalpha())
    suspicious_chars = text.count("�") + text.count("\x00")
    density = (alnum_count / non_whitespace) if non_whitespace else 0.0
    reasons: list[str] = []

    if text_char_count == 0 or non_whitespace == 0:
        reasons.append("empty_text")
    if non_whitespace and non_whitespace < 16:
        reasons.append("very_short_text")
    elif non_whitespace < 120:
        reasons.append("short_text")
    if parsed.extraction_method == "ocr":
        reasons.append("ocr_source")
    if suspicious_chars:
        reasons.append("suspicious_characters")
    if non_whitespace and density < 0.35:
        reasons.append("low_alnum_density")
    if non_whitespace and alpha_count < 8:
        reasons.append("low_alpha_count")
    if any("empty" in warning for warning in parsed.warnings):
        reasons.append("partial_empty_blocks")

    suspicious = any(
        reason in reasons
        for reason in ("suspicious_characters", "low_alnum_density", "low_alpha_count")
    )

    if "empty_text" in reasons or "very_short_text" in reasons or suspicious:
        quality: Literal["high", "medium", "low"] = "low"
    elif parsed.extraction_method == "ocr" or "short_text" in reasons or parsed.warnings:
        quality = "medium"
    else:
        quality = "high"

    return replace(
        parsed,
        extraction_quality=quality,
        quality_reasons=reasons,
        text_char_count=text_char_count,
        non_whitespace_char_count=non_whitespace,
        suspicious_text=suspicious,
        ocr_used=parsed.extraction_method == "ocr",
    )


def extract_text_from_pdf(
    path: str | Path,
    *,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
    max_pages: int = DEFAULT_MAX_PAGES,
    ocr_fallback: bool = False,
) -> ParsedDocument:
    pdf_path = Path(path)
    _validate_source_file(pdf_path, expected_suffix=".pdf", max_file_mb=max_file_mb)

    warnings: list[str] = []
    try:
        reader = PdfReader(str(pdf_path))
    except PdfReadError as e:
        raise DocumentPipelineError(f"Битый или нечитаемый PDF: {pdf_path.name}: {e}") from e
    except Exception as e:
        raise DocumentPipelineError(f"Не удалось открыть PDF {pdf_path.name}: {e}") from e

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as e:
            raise DocumentPipelineError(f"PDF зашифрован и не читается без пароля: {pdf_path.name}") from e

    page_count = len(reader.pages)
    if page_count == 0:
        raise DocumentPipelineError(f"В PDF нет страниц: {pdf_path.name}")
    if page_count > max_pages:
        raise DocumentPipelineError(
            f"PDF слишком длинный: {pdf_path.name} ({page_count} pages > {max_pages})"
        )

    blocks: list[ParsedDocumentBlock] = []
    text_layer_found = False
    for page_index, page in enumerate(reader.pages, start=1):
        text = pdf.normalize_extracted_text(page.extract_text() or "")
        if text:
            text_layer_found = True
            blocks.append(
                ParsedDocumentBlock(index=len(blocks) + 1, page_number=page_index, text=text, kind="page")
            )
        else:
            warnings.append(f"page_{page_index}_empty")

    if not blocks:
        user_safe_reason = (
            "В PDF не найден текстовый слой, но страницы документа присутствуют. "
            "Документ выглядит как скан; для анализа нужен OCR/visual fallback."
        )
        msg = user_safe_reason
        if ocr_fallback:
            msg += " OCR fallback requested, but degraded OCR mode is not configured."
        else:
            msg += " OCR fallback не включён."
        raise DocumentPipelineError(
            msg,
            code="no_text_layer_but_pages_present",
            user_safe_reason=user_safe_reason,
            debug_info={
                "source_kind": "pdf",
                "text_layer_found": False,
                "pages_present": page_count > 0,
                "pages_count": page_count,
                "fallback_used": "tech_notice",
                "extraction_status": "no_text_layer_but_pages_present",
                "user_safe_reason": user_safe_reason,
            },
        )

    return _build_parsed_document(
        source_path=pdf_path,
        file_type="pdf",
        extraction_method="pypdf",
        blocks=blocks,
        warnings=warnings,
        page_count=page_count,
        extraction_status="text_extracted",
        text_layer_found=text_layer_found,
        pages_present=page_count > 0,
        fallback_used="none",
        user_safe_reason=None,
    )


def extract_text_from_docx(
    path: str | Path,
    *,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
) -> ParsedDocument:
    docx_path = Path(path)
    _validate_source_file(docx_path, expected_suffix=".docx", max_file_mb=max_file_mb)

    try:
        with zipfile.ZipFile(docx_path) as zf:
            xml_bytes = zf.read("word/document.xml")
    except KeyError as e:
        raise DocumentPipelineError(f"Битый DOCX: отсутствует word/document.xml в {docx_path.name}") from e
    except zipfile.BadZipFile as e:
        raise DocumentPipelineError(f"Битый DOCX: {docx_path.name}: {e}") from e
    except Exception as e:
        raise DocumentPipelineError(f"Не удалось открыть DOCX {docx_path.name}: {e}") from e

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise DocumentPipelineError(f"DOCX содержит повреждённый XML: {docx_path.name}: {e}") from e

    body = root.find("w:body", _WORD_NS)
    if body is None:
        raise DocumentPipelineError(f"Не удалось прочитать содержимое DOCX: {docx_path.name}")

    blocks: list[ParsedDocumentBlock] = []
    for child in list(body):
        tag = _local_name(child.tag)
        if tag == "p":
            text = pdf.normalize_extracted_text(_extract_docx_paragraph(child))
            if text:
                blocks.append(ParsedDocumentBlock(index=len(blocks) + 1, text=text, kind="paragraph"))
        elif tag == "tbl":
            text = pdf.normalize_extracted_text(_extract_docx_table(child))
            if text:
                blocks.append(ParsedDocumentBlock(index=len(blocks) + 1, text=text, kind="table"))

    if not blocks:
        raise DocumentPipelineError(f"В DOCX не удалось извлечь текст: {docx_path.name}")

    return _build_parsed_document(
        source_path=docx_path,
        file_type="docx",
        extraction_method="docx",
        blocks=blocks,
        warnings=[],
        page_count=1,
        extraction_status="text_extracted",
        text_layer_found=None,
        pages_present=True,
        fallback_used="none",
        user_safe_reason=None,
    )


def extract_text_from_txt(
    path: str | Path,
    *,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
) -> ParsedDocument:
    txt_path = Path(path)
    _validate_source_file(txt_path, expected_suffix=".txt", max_file_mb=max_file_mb)

    data = txt_path.read_bytes()
    decoded: str | None = None
    used_encoding: str | None = None
    for encoding in ("utf-8", "utf-8-sig", "cp1251"):
        try:
            decoded = data.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if decoded is None or used_encoding is None:
        raise DocumentPipelineError(
            f"Не удалось декодировать TXT {txt_path.name}; tried utf-8/utf-8-sig/cp1251"
        )

    text = pdf.normalize_extracted_text(decoded)
    if not text:
        raise DocumentPipelineError(f"TXT пустой после нормализации: {txt_path.name}")

    warnings = [] if used_encoding == "utf-8" else [f"encoding_{used_encoding}"]
    return _build_parsed_document(
        source_path=txt_path,
        file_type="txt",
        extraction_method="plain_text",
        blocks=[ParsedDocumentBlock(index=1, text=text, kind="text")],
        warnings=warnings,
        page_count=1,
        extraction_status="text_extracted",
        text_layer_found=None,
        pages_present=True,
        fallback_used="none",
        user_safe_reason=None,
    )


def extract_text_from_image(
    path: str | Path,
    *,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
    enable_ocr: bool = True,
) -> ParsedDocument:
    image_path = Path(path)
    _validate_source_file(image_path, max_file_mb=max_file_mb)
    if image_path.suffix.lower() not in _IMAGE_SUFFIXES:
        raise DocumentPipelineError(f"unsupported image type: {image_path.name}")
    if not enable_ocr:
        raise DocumentPipelineError("OCR backend unavailable or not configured for image extraction.")

    pytesseract = _load_ocr_backend()
    try:
        with Image.open(image_path) as img:
            raw = pytesseract.image_to_string(img, lang="rus+eng")
    except DocumentPipelineError:
        raise
    except Exception as e:
        raise DocumentPipelineError(f"Не удалось прочитать изображение {image_path.name}: {e}") from e

    text = pdf.normalize_extracted_text(raw)
    if not text:
        raise DocumentPipelineError(
            f"OCR не извлёк текст из изображения {image_path.name}. Проверьте качество скана или OCR backend."
        )

    warnings: list[str] = []
    if len(text) < 40:
        warnings.append("low_ocr_text")
    return _build_parsed_document(
        source_path=image_path,
        file_type="image",
        extraction_method="ocr",
        blocks=[ParsedDocumentBlock(index=1, text=text, kind="image")],
        warnings=warnings,
        page_count=1,
        extraction_status="ocr_extracted",
        text_layer_found=None,
        pages_present=True,
        fallback_used="ocr",
        user_safe_reason=None,
    )


def save_extracted_text(
    parsed: ParsedDocument,
    *,
    artifact_base_name: str,
    output_dir: str | Path | None = None,
) -> Path:
    target_dir = Path(output_dir) if output_dir is not None else Path.cwd() / "artifacts" / "document-text"
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / f"{artifact_base_name}.txt"
    out.write_text(parsed.text, encoding="utf-8")
    return out


def save_analysis_artifact(result: dict[str, Any], *, analysis_path: str | Path) -> Path:
    out = Path(analysis_path)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def build_document_chunks(
    blocks: list[ParsedDocumentBlock],
    *,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[pdf.PdfChunk]:
    pseudo_pages = [
        pdf.PdfPageText(page_number=block.page_number or block.index, text=block.text)
        for block in blocks
    ]
    return pdf.build_pdf_chunks(pseudo_pages, max_chars=max_chars, overlap=overlap)


async def analyze_document(
    path: str | Path,
    *,
    task: DocumentTask = "claim_response",
    reply_mode: ClaimReplyMode = "auto",
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
    max_pages: int = DEFAULT_MAX_PAGES,
    chunk_max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    direct_text_limit: int = DEFAULT_DIRECT_TEXT_LIMIT,
    output_dir: str | Path | None = None,
    enable_ocr_fallback: bool = False,
) -> DocumentAnalysisResult:
    parsed = extract_text_from_document(
        path,
        max_file_mb=max_file_mb,
        max_pages=max_pages,
        enable_ocr_fallback=enable_ocr_fallback,
    )
    source_path = Path(parsed.source_path)
    source_hash = compute_file_sha256(source_path)
    created_at_utc = datetime.now(timezone.utc).isoformat()
    run_id = build_run_id(created_at_utc, source_hash)
    artifact_base_name = build_artifact_base_name(source_path, task=task, run_id=run_id)
    text_path = save_extracted_text(parsed, artifact_base_name=artifact_base_name, output_dir=output_dir)
    chunks = build_document_chunks(parsed.blocks, max_chars=chunk_max_chars, overlap=chunk_overlap)

    async with httpx.AsyncClient() as client:
        source_text = await _build_prompt_source(
            client,
            task=task,
            parsed=parsed,
            chunks=chunks,
            direct_text_limit=direct_text_limit,
        )
        response_text = await chat_raw(
            system=_build_task_system_prompt(task),
            user=_build_task_user_prompt(task, parsed, source_text),
            client=client,
        )

        try:
            if task == "claim_response":
                payload = pdf.extract_structured_claim_response(response_text)
                effective_reply_mode = pdf.resolve_claim_reply_mode(
                    payload["extracted_facts"],
                    requested_mode=reply_mode,
                )
                if reply_mode == "auto" and parsed.extraction_quality == "low":
                    effective_reply_mode = "request_documents"
                payload["reply_mode_requested"] = reply_mode
                payload["reply_mode_effective"] = effective_reply_mode
                payload["draft_reply"] = await pdf.generate_claim_reply_from_facts(
                    payload,
                    client=client,
                    reply_mode=effective_reply_mode if reply_mode == "auto" else reply_mode,
                    chat_func=chat_raw,
                )
            else:
                payload = pdf._normalize_analysis_payload(pdf.parse_llm_json_response(response_text))
        except Exception as e:
            raise DocumentPipelineError(f"Модель вернула невалидный JSON-ответ: {e}") from e

    warnings = _merge_analysis_warnings(parsed, task=task)
    raw_response = {
        **payload,
        "run_id": run_id,
        "created_at_utc": created_at_utc,
        "source_file_name": source_path.name,
        "source_file_hash_sha256": source_hash,
        "model_used": settings.chat_model,
        "source_path": parsed.source_path,
        "file_type": parsed.file_type,
        "file_size_bytes": parsed.file_size_bytes,
        "extraction_method": parsed.extraction_method,
        "extraction_quality": parsed.extraction_quality,
        "quality_reasons": parsed.quality_reasons,
        "text_char_count": parsed.text_char_count,
        "non_whitespace_char_count": parsed.non_whitespace_char_count,
        "suspicious_text": parsed.suspicious_text,
        "ocr_used": parsed.ocr_used,
        "source_kind": parsed.file_type,
        "extraction_status": parsed.extraction_status,
        "text_layer_found": parsed.text_layer_found,
        "pages_present": parsed.pages_present,
        "pages_count": parsed.page_count,
        "fallback_used": parsed.fallback_used,
        "user_safe_reason": parsed.user_safe_reason,
        "warnings": warnings,
        "task": task,
        "reply_mode_requested": payload.get("reply_mode_requested"),
        "reply_mode_effective": payload.get("reply_mode_effective"),
        "text_saved_path": str(text_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    analysis_path = Path(text_path).with_suffix(".analysis.json")
    raw_response["analysis_saved_path"] = str(analysis_path)
    analysis_path = save_analysis_artifact(raw_response, analysis_path=analysis_path)

    return DocumentAnalysisResult(
        task=task,
        run_id=run_id,
        created_at_utc=created_at_utc,
        source_file_name=source_path.name,
        source_file_hash_sha256=source_hash,
        model_used=settings.chat_model,
        source_path=parsed.source_path,
        file_type=parsed.file_type,
        extraction_method=parsed.extraction_method,
        extraction_quality=parsed.extraction_quality,
        quality_reasons=parsed.quality_reasons,
        text_char_count=parsed.text_char_count,
        non_whitespace_char_count=parsed.non_whitespace_char_count,
        suspicious_text=parsed.suspicious_text,
        ocr_used=parsed.ocr_used,
        extraction_status=parsed.extraction_status,
        text_layer_found=parsed.text_layer_found,
        pages_present=parsed.pages_present,
        fallback_used=parsed.fallback_used,
        user_safe_reason=parsed.user_safe_reason,
        text_path=str(text_path),
        analysis_path=str(analysis_path),
        page_count=parsed.page_count,
        block_count=len(parsed.blocks),
        chunk_count=max(1, len(chunks)),
        summary=payload["summary"],
        extracted_facts=payload["extracted_facts"],
        draft_reply=payload["draft_reply"],
        warnings=warnings,
        raw_response=raw_response,
        reply_mode_requested=payload.get("reply_mode_requested"),
        reply_mode_effective=payload.get("reply_mode_effective"),
    )


async def analyze_pdf_document(
    path: str | Path,
    *,
    task: DocumentTask = "claim_response",
    reply_mode: ClaimReplyMode = "auto",
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
    max_pages: int = DEFAULT_MAX_PAGES,
    chunk_max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    direct_text_limit: int = DEFAULT_DIRECT_TEXT_LIMIT,
    output_dir: str | Path | None = None,
    ocr_fallback: bool = False,
) -> DocumentAnalysisResult:
    return await analyze_document(
        path,
        task=task,
        reply_mode=reply_mode,
        max_file_mb=max_file_mb,
        max_pages=max_pages,
        chunk_max_chars=chunk_max_chars,
        chunk_overlap=chunk_overlap,
        direct_text_limit=direct_text_limit,
        output_dir=output_dir,
        enable_ocr_fallback=ocr_fallback,
    )


def compute_file_sha256(path: str | Path) -> str:
    file_path = Path(path)
    h = hashlib.sha256()
    with file_path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_run_id(created_at_utc: str, source_hash: str) -> str:
    timestamp = created_at_utc.replace("-", "").replace(":", "").replace("+00:00", "Z")
    if "." in timestamp:
        prefix, suffix = timestamp.split(".", 1)
        digits = "".join(ch for ch in suffix if ch.isdigit())[:6].ljust(6, "0")
        timestamp = f"{prefix}{digits}Z"
    return f"{timestamp}_{source_hash[:8]}"


def build_artifact_base_name(source_path: Path, *, task: DocumentTask, run_id: str) -> str:
    safe_stem = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in source_path.stem).strip("._")
    safe_stem = safe_stem or "document"
    safe_task = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in task)
    return f"{safe_stem}.{safe_task}.{run_id}"


def _build_parsed_document(
    *,
    source_path: Path,
    file_type: DocumentType,
    extraction_method: str,
    blocks: list[ParsedDocumentBlock],
    warnings: list[str],
    page_count: int,
    extraction_status: str,
    text_layer_found: bool | None,
    pages_present: bool,
    fallback_used: Literal["none", "ocr", "vision", "tech_notice"],
    user_safe_reason: str | None,
) -> ParsedDocument:
    text = "\n\n".join(block.text for block in blocks).strip()
    if not text:
        raise DocumentPipelineError(
            f"empty extracted text: {source_path.name}",
            code="no_readable_content",
            debug_info={
                "source_kind": file_type,
                "text_layer_found": text_layer_found,
                "pages_present": pages_present,
                "pages_count": page_count,
                "fallback_used": fallback_used,
                "extraction_status": "no_readable_content",
                "user_safe_reason": user_safe_reason or "Автоматическое извлечение текста не удалось.",
            },
            user_safe_reason=user_safe_reason or "Автоматическое извлечение текста не удалось.",
        )
    parsed = ParsedDocument(
        source_path=str(source_path),
        file_type=file_type,
        file_size_bytes=source_path.stat().st_size,
        text=text,
        blocks=blocks,
        warnings=warnings,
        extraction_method=extraction_method,
        page_count=page_count,
        extraction_status=extraction_status,
        text_layer_found=text_layer_found,
        pages_present=pages_present,
        fallback_used=fallback_used,
        user_safe_reason=user_safe_reason,
    )
    return assess_extraction_quality(parsed)


async def _build_prompt_source(
    client: httpx.AsyncClient,
    *,
    task: DocumentTask,
    parsed: ParsedDocument,
    chunks: list[pdf.PdfChunk],
    direct_text_limit: int,
) -> str:
    if len(parsed.text) <= direct_text_limit or len(chunks) <= 1:
        return "\n\n---\n\n".join(
            f"[{_block_label(block)}]\n{block.text}" for block in parsed.blocks
        )

    chunk_notes: list[str] = []
    for chunk in chunks:
        note = await chat_raw(
            client=client,
            system=pdf._CHUNK_SYSTEM,
            user=(
                f"Сценарий: {task}\n"
                f"Диапазон: {chunk.page_range_label}\n\n"
                f"Текст фрагмента:\n{chunk.text}"
            ),
        )
        chunk_notes.append(f"[{chunk.page_range_label}]\n{note.strip()}")
    return "\n\n---\n\n".join(chunk_notes)


def _build_task_system_prompt(task: DocumentTask) -> str:
    schema = pdf._CLAIM_RESPONSE_SCHEMA if task == "claim_response" else pdf._TASK_SCHEMA
    return (
        f"{pdf._BASE_SYSTEM}\n\n"
        f"Задача: {pdf._TASK_INSTRUCTIONS[task]}\n\n"
        f"Верни только один JSON-объект без markdown. Схема:\n{schema}"
    )


def _build_task_user_prompt(task: DocumentTask, parsed: ParsedDocument, source_text: str) -> str:
    return (
        f"Файл: {Path(parsed.source_path).name}\n"
        f"Тип: {parsed.file_type}\n"
        f"Метод extraction: {parsed.extraction_method}\n"
        f"Качество extraction: {parsed.extraction_quality}\n"
        f"Причины качества: {', '.join(parsed.quality_reasons) if parsed.quality_reasons else 'none'}\n"
        f"Блоков: {len(parsed.blocks)}\n\n"
        f"Извлечённый текст документа:\n\n{source_text}\n\n"
        "Требования:\n"
        "- Не выдумывай отсутствующие факты.\n"
        "- Если реквизит, сумма, срок или дата не найдены — так и напиши.\n"
        "- Для claim_response draft_reply должен быть официальным ответом на русском.\n"
        "- Для остальных задач draft_reply можно оставить пустой строкой.\n"
    )


def _merge_analysis_warnings(parsed: ParsedDocument, *, task: DocumentTask) -> list[str]:
    warnings = list(parsed.warnings)
    if parsed.extraction_quality == "low":
        warnings.append("low_extraction_quality")
        if task == "claim_response":
            warnings.append("claim_response_based_on_low_quality_extraction")
    return warnings


def _extract_docx_paragraph(node: ET.Element) -> str:
    parts: list[str] = []
    for child in node.iter():
        tag = _local_name(child.tag)
        if tag == "t" and child.text:
            parts.append(child.text)
        elif tag in {"br", "cr"}:
            parts.append("\n")
        elif tag == "tab":
            parts.append("\t")
    return "".join(parts)


def _extract_docx_table(node: ET.Element) -> str:
    rows: list[str] = []
    for tr in node.findall("w:tr", _WORD_NS):
        cells: list[str] = []
        for tc in tr.findall("w:tc", _WORD_NS):
            cell_parts = [
                _extract_docx_paragraph(p)
                for p in tc.findall("w:p", _WORD_NS)
            ]
            cell_text = " ".join(part.strip() for part in cell_parts if part.strip())
            if cell_text:
                cells.append(cell_text)
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _validate_source_file(
    path: Path,
    *,
    expected_suffix: str | None = None,
    max_file_mb: int,
) -> None:
    if not path.is_file():
        raise DocumentPipelineError(f"Файл не найден: {path}")
    if expected_suffix and path.suffix.lower() != expected_suffix:
        raise DocumentPipelineError(f"Ожидался файл {expected_suffix}: {path.name}")
    size_limit = max_file_mb * 1024 * 1024
    size_bytes = path.stat().st_size
    if size_bytes <= 0:
        raise DocumentPipelineError(f"Файл пустой: {path.name}")
    if size_bytes > size_limit:
        raise DocumentPipelineError(
            f"Файл слишком большой: {path.name} ({size_bytes} bytes > {size_limit})"
        )


def _block_label(block: ParsedDocumentBlock) -> str:
    if block.page_number is not None:
        return f"Page {block.page_number}"
    return f"Block {block.index}"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _load_ocr_backend():
    if importlib.util.find_spec("pytesseract") is None:
        raise DocumentPipelineError("OCR backend unavailable: pytesseract not installed or not configured.")
    import pytesseract  # type: ignore

    try:
        pytesseract.get_tesseract_version()
    except Exception as e:
        raise DocumentPipelineError(f"OCR backend unavailable: {e}") from e
    return pytesseract
