from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.generation.ollama_client import chat_raw
from app.services.json_extract import parse_json_object


PdfTask = Literal[
    "summary",
    "key_facts",
    "claim_response",
    "contract_risk_review",
    "invoice_requisites",
]
ClaimReplyMode = Literal["neutral", "deny", "request_documents", "settlement", "auto"]
SUPPORTED_PDF_TASKS: tuple[PdfTask, ...] = (
    "summary",
    "key_facts",
    "claim_response",
    "contract_risk_review",
    "invoice_requisites",
)
SUPPORTED_CLAIM_REPLY_MODES: tuple[ClaimReplyMode, ...] = (
    "neutral",
    "deny",
    "request_documents",
    "settlement",
    "auto",
)

DEFAULT_MAX_FILE_MB = 15
DEFAULT_MAX_PAGES = 200
DEFAULT_CHUNK_MAX_CHARS = 6000
DEFAULT_CHUNK_OVERLAP = 400
DEFAULT_DIRECT_TEXT_LIMIT = 12000
_UNKNOWN = "unknown"


class PdfDocumentError(RuntimeError):
    """Понятная ошибка обработки PDF без молчаливого падения."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "pdf_error",
        debug_info: dict[str, Any] | None = None,
        user_safe_reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.debug_info = debug_info or {}
        self.user_safe_reason = user_safe_reason or message


@dataclass(frozen=True)
class PdfPageText:
    page_number: int
    text: str


@dataclass(frozen=True)
class PdfChunk:
    index: int
    start_page: int
    end_page: int
    text: str

    @property
    def page_range_label(self) -> str:
        if self.start_page == self.end_page:
            return str(self.start_page)
        return f"{self.start_page}-{self.end_page}"


@dataclass(frozen=True)
class PdfParseResult:
    source_path: str
    text: str
    page_count: int
    pages: list[PdfPageText]
    warnings: list[str]
    extraction_status: str = "text_extracted"
    text_layer_found: bool = True
    pages_present: bool = True
    fallback_used: str = "none"
    user_safe_reason: str | None = None


@dataclass(frozen=True)
class PdfAnalysisResult:
    task: PdfTask
    source_path: str
    text_path: str
    page_count: int
    chunk_count: int
    summary: str
    extracted_facts: dict[str, Any]
    draft_reply: str
    warnings: list[str]
    raw_response: dict[str, Any]
    reply_mode_requested: str | None = None
    reply_mode_effective: str | None = None


_BASE_SYSTEM = (
    "Ты локальный помощник по разбору PDF-документов на русском языке. "
    "Опирайся только на извлечённый текст документа. Не выдумывай факты, суммы, сроки и реквизиты. "
    "Если данных в тексте нет или они нечитабельны — прямо так и укажи. "
    "Это не юридическое заключение; ответ требует ручной проверки."
)

_CHUNK_SYSTEM = (
    "Ты анализируешь только часть PDF-документа. "
    "Верни короткие bullets на русском: стороны, требования, суммы, даты, сроки, документы, риски, реквизиты. "
    "Не делай итог за весь документ, только факты из этого фрагмента."
)

_CLAIM_REPLY_SYSTEM = (
    "Ты готовишь официальный ответ на претензию на русском языке. "
    "Используй только summary и extracted_facts, которые переданы ниже. "
    "Запрещено добавлять факты, суммы, даты, реквизиты, номера документов и признания, которых нет во входных данных. "
    "Если данных мало, пиши сдержанно: по результатам рассмотрения, при наличии подтверждающих документов, просим направить материалы, сообщим позицию дополнительно. "
    "Тон деловой, официальный, без LLM-стиля и без markdown."
)

_CLAIM_REPLY_MODE_GUIDANCE: dict[str, str] = {
    "neutral": (
        "Спокойный официальный ответ без лишних признаний и без излишней конфронтации. "
        "Излагай позицию сдержанно и деловито."
    ),
    "deny": (
        "Акцент на несогласии с требованиями. Не признавай долг, нарушение, вину или обязанность оплаты, "
        "если это прямо не подтверждено facts."
    ),
    "request_documents": (
        "Акцент на недостаточности материалов. Проси направить подтверждающие документы, расчёты, акты, переписку и иные доказательства."
    ),
    "settlement": (
        "Мягкий деловой тон с готовностью обсудить урегулирование. Не признавай автоматически долг или ответственность."
    ),
}

_TASK_INSTRUCTIONS: dict[PdfTask, str] = {
    "summary": (
        "Подготовь краткое содержание документа. "
        "В extracted_facts перечисли тип документа, ключевые стороны, даты, суммы и ссылки на приложения, если они есть. "
        "draft_reply оставь пустой строкой."
    ),
    "key_facts": (
        "Извлеки ключевые факты документа. "
        "В extracted_facts структурируй стороны, номера документов, даты, суммы, сроки, приложения и важные обстоятельства. "
        "draft_reply оставь пустой строкой."
    ),
    "claim_response": (
        "Это режим ответа на претензию. "
        "Верни только JSON строго по схеме claim_response. "
        "Определи отправителя и получателя, суть требований, суммы, даты, ссылки на документы и обстоятельства, срок ответа и возможную позицию адресата. "
        "Если данных нет, используй 'unknown' для строк и [] для списков. "
        "Ничего не выдумывай; пробелы фиксируй в missing_information. "
        "Подготовь draft_reply как официальный деловой ответ на русском языке только на основе извлечённого текста."
    ),
    "contract_risk_review": (
        "Это обзор рисков договора. "
        "В extracted_facts собери стороны, предмет, платежи, сроки, ответственность, спорные формулировки и список рисков. "
        "draft_reply используй для короткого перечня рекомендуемых правок."
    ),
    "invoice_requisites": (
        "Это извлечение реквизитов и финансовых данных. "
        "В extracted_facts собери плательщика, получателя, ИНН/КПП, расчётные счета, банк, БИК, суммы, НДС, номера счетов/актов. "
        "draft_reply оставь пустой строкой."
    ),
}

_TASK_SCHEMA = """
{
  "summary": "краткая сводка на русском",
  "extracted_facts": {
    "document_type": "",
    "sender": "",
    "recipient": "",
    "amounts": [],
    "dates": [],
    "deadlines": [],
    "document_refs": [],
    "risks": [],
    "notes": []
  },
  "draft_reply": "для задач без ответа — пустая строка"
}
""".strip()

_CLAIM_RESPONSE_SCHEMA = """
{
  "summary": "краткая сводка",
  "extracted_facts": {
    "sender": "строка или unknown",
    "recipient": "строка или unknown",
    "claim_subject": "строка или unknown",
    "claim_amounts": ["список сумм"],
    "dates": ["список дат"],
    "referenced_documents": ["список документов/актов/договоров"],
    "response_deadline": "строка или unknown",
    "recipient_position": "строка или unknown",
    "legal_risks": ["список рисков"],
    "missing_information": ["что не удалось надёжно извлечь"]
  },
  "draft_reply": "официальный ответ на русском языке или unknown"
}
""".strip()


def extract_text_from_pdf(
    path: str | Path,
    *,
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
    max_pages: int = DEFAULT_MAX_PAGES,
    ocr_fallback: bool = False,
) -> PdfParseResult:
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise PdfDocumentError(f"PDF не найден: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise PdfDocumentError(f"Ожидался .pdf файл: {pdf_path.name}")

    size_limit = max_file_mb * 1024 * 1024
    size_bytes = pdf_path.stat().st_size
    if size_bytes <= 0:
        raise PdfDocumentError(f"PDF пустой: {pdf_path.name}")
    if size_bytes > size_limit:
        raise PdfDocumentError(
            f"PDF слишком большой: {pdf_path.name} ({size_bytes} bytes > {size_limit})"
        )

    warnings: list[str] = []
    try:
        reader = PdfReader(str(pdf_path))
    except PdfReadError as e:
        raise PdfDocumentError(f"Битый или нечитаемый PDF: {pdf_path.name}: {e}") from e
    except Exception as e:
        raise PdfDocumentError(f"Не удалось открыть PDF {pdf_path.name}: {e}") from e

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as e:
            raise PdfDocumentError(f"PDF зашифрован и не читается без пароля: {pdf_path.name}") from e

    page_count = len(reader.pages)
    if page_count == 0:
        raise PdfDocumentError(f"В PDF нет страниц: {pdf_path.name}")
    if page_count > max_pages:
        raise PdfDocumentError(
            f"PDF слишком длинный: {pdf_path.name} ({page_count} pages > {max_pages})"
        )

    pages: list[PdfPageText] = []
    text_layer_found = False
    for page_index, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        normalized = _normalize_pdf_text(raw)
        if normalized:
            text_layer_found = True
            pages.append(PdfPageText(page_number=page_index, text=normalized))
        else:
            warnings.append(f"page_{page_index}_empty")

    if not pages:
        user_safe_reason = (
            "В PDF не найден текстовый слой, но страницы документа присутствуют. "
            "Документ выглядит как скан; для анализа нужен OCR/visual fallback."
        )
        msg = user_safe_reason
        if ocr_fallback:
            msg += " OCR fallback requested, but degraded OCR mode is not configured."
        else:
            msg += " OCR fallback не включён."
        raise PdfDocumentError(
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

    full_text = "\n\n".join(page.text for page in pages).strip()
    if not full_text:
        raise PdfDocumentError(
            "После нормализации извлечённый текст оказался пустым.",
            code="no_readable_content",
            debug_info={
                "source_kind": "pdf",
                "text_layer_found": text_layer_found,
                "pages_present": page_count > 0,
                "pages_count": page_count,
                "fallback_used": "none",
                "extraction_status": "no_readable_content",
                "user_safe_reason": "Автоматическое извлечение текста не удалось; проверьте документ.",
            },
        )

    return PdfParseResult(
        source_path=str(pdf_path),
        text=full_text,
        page_count=page_count,
        pages=pages,
        warnings=warnings,
        extraction_status="text_extracted",
        text_layer_found=True,
        pages_present=page_count > 0,
        fallback_used="none",
        user_safe_reason=None,
    )


def build_pdf_chunks(
    pages: list[PdfPageText],
    *,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[PdfChunk]:
    if max_chars < 500:
        raise ValueError("max_chars слишком маленький")
    if overlap < 0:
        raise ValueError("overlap не может быть отрицательным")

    segments = _page_paragraph_segments(pages, max_chars=max_chars)
    if not segments:
        return []

    chunks: list[PdfChunk] = []
    start = 0
    while start < len(segments):
        end = start
        total = 0
        used: list[tuple[int, str]] = []
        while end < len(segments):
            page_no, segment = segments[end]
            add_len = len(segment) + (2 if used else 0)
            if used and total + add_len > max_chars:
                break
            used.append((page_no, segment))
            total += add_len
            end += 1

        start_page = used[0][0]
        end_page = used[-1][0]
        chunk_text = "\n\n".join(segment for _, segment in used)
        chunks.append(
            PdfChunk(
                index=len(chunks) + 1,
                start_page=start_page,
                end_page=end_page,
                text=chunk_text,
            )
        )

        if end >= len(segments):
            break

        if len(used) == 1:
            start = end
            continue

        overlap_chars = 0
        next_start = end
        for idx in range(end - 1, start - 1, -1):
            overlap_chars += len(segments[idx][1]) + 2
            next_start = idx
            if overlap_chars >= overlap:
                break
        start = next_start if next_start > start else end

    return chunks


def save_extracted_text(
    parsed: PdfParseResult,
    *,
    output_dir: str | Path | None = None,
) -> Path:
    src = Path(parsed.source_path)
    target_dir = Path(output_dir) if output_dir is not None else Path.cwd() / "artifacts" / "document-text"
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / f"{src.stem}.txt"
    out.write_text(parsed.text, encoding="utf-8")
    return out


async def analyze_pdf_document(
    path: str | Path,
    *,
    task: PdfTask = "claim_response",
    max_file_mb: int = DEFAULT_MAX_FILE_MB,
    max_pages: int = DEFAULT_MAX_PAGES,
    chunk_max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    direct_text_limit: int = DEFAULT_DIRECT_TEXT_LIMIT,
    output_dir: str | Path | None = None,
    ocr_fallback: bool = False,
    reply_mode: ClaimReplyMode = "auto",
) -> PdfAnalysisResult:
    parsed = extract_text_from_pdf(
        path,
        max_file_mb=max_file_mb,
        max_pages=max_pages,
        ocr_fallback=ocr_fallback,
    )
    text_path = save_extracted_text(parsed, output_dir=output_dir)
    chunks = build_pdf_chunks(
        parsed.pages,
        max_chars=chunk_max_chars,
        overlap=chunk_overlap,
    )

    async with httpx.AsyncClient() as client:
        source_text = await _build_prompt_source(
            client,
            task=task,
            parsed=parsed,
            chunks=chunks,
            direct_text_limit=direct_text_limit,
        )
        system_prompt = _build_task_system_prompt(task)
        user_prompt = _build_task_user_prompt(task, parsed, source_text)
        response_text = await chat_raw(system=system_prompt, user=user_prompt, client=client)

        try:
            if task == "claim_response":
                payload = extract_structured_claim_response(response_text)
                effective_reply_mode = resolve_claim_reply_mode(
                    payload["extracted_facts"],
                    requested_mode=reply_mode,
                )
                payload["reply_mode_requested"] = reply_mode
                payload["reply_mode_effective"] = effective_reply_mode
                payload["draft_reply"] = await generate_claim_reply_from_facts(
                    payload,
                    client=client,
                    reply_mode=reply_mode,
                )
            else:
                payload = _normalize_analysis_payload(parse_llm_json_response(response_text))
        except Exception as e:
            raise PdfDocumentError(f"Модель вернула невалидный JSON-ответ: {e}") from e

    return PdfAnalysisResult(
        task=task,
        source_path=parsed.source_path,
        text_path=str(text_path),
        page_count=parsed.page_count,
        chunk_count=max(1, len(chunks)),
        summary=payload["summary"],
        extracted_facts=payload["extracted_facts"],
        draft_reply=payload["draft_reply"],
        reply_mode_requested=payload.get("reply_mode_requested"),
        reply_mode_effective=payload.get("reply_mode_effective"),
        warnings=parsed.warnings,
        raw_response=payload,
    )


def _normalize_pdf_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00ad", "")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    paragraphs: list[str] = []
    current: list[str] = []
    for line in text.split("\n"):
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    normalized = "\n\n".join(paragraphs)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


normalize_extracted_text = _normalize_pdf_text


def _page_paragraph_segments(
    pages: list[PdfPageText],
    *,
    max_chars: int,
) -> list[tuple[int, str]]:
    segments: list[tuple[int, str]] = []
    for page in pages:
        paragraphs = [p.strip() for p in page.text.split("\n\n") if p.strip()]
        if not paragraphs:
            continue
        for paragraph in paragraphs:
            for piece in _split_long_piece(paragraph, max_chars=max_chars):
                segments.append((page.page_number, piece))
    return segments


def _split_long_piece(text: str, *, max_chars: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) == 1:
        return _split_by_whitespace_window(text, max_chars=max_chars)

    pieces: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        add_len = len(sentence) + (1 if current else 0)
        if current and current_len + add_len > max_chars:
            pieces.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += add_len
    if current:
        pieces.append(" ".join(current))

    out: list[str] = []
    for piece in pieces:
        if len(piece) <= max_chars:
            out.append(piece)
        else:
            out.extend(_split_by_whitespace_window(piece, max_chars=max_chars))
    return out


def _split_by_whitespace_window(text: str, *, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    pieces: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        add_len = len(word) + (1 if current else 0)
        if current and current_len + add_len > max_chars:
            pieces.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += add_len
    if current:
        pieces.append(" ".join(current))
    return pieces


async def _build_prompt_source(
    client: httpx.AsyncClient,
    *,
    task: PdfTask,
    parsed: PdfParseResult,
    chunks: list[PdfChunk],
    direct_text_limit: int,
) -> str:
    if len(parsed.text) <= direct_text_limit or len(chunks) <= 1:
        page_blocks = [
            f"[Страницы {page.page_number}]\n{page.text}"
            for page in parsed.pages
        ]
        return "\n\n---\n\n".join(page_blocks)

    chunk_notes: list[str] = []
    for chunk in chunks:
        note = await chat_raw(
            client=client,
            system=_CHUNK_SYSTEM,
            user=(
                f"Сценарий: {task}\n"
                f"Страницы: {chunk.page_range_label}\n\n"
                f"Текст фрагмента:\n{chunk.text}"
            ),
        )
        chunk_notes.append(f"[Страницы {chunk.page_range_label}]\n{note.strip()}")
    return "\n\n---\n\n".join(chunk_notes)


def _build_task_system_prompt(task: PdfTask) -> str:
    schema = _CLAIM_RESPONSE_SCHEMA if task == "claim_response" else _TASK_SCHEMA
    return (
        f"{_BASE_SYSTEM}\n\n"
        f"Задача: {_TASK_INSTRUCTIONS[task]}\n\n"
        f"Верни только один JSON-объект без markdown. Схема:\n{schema}"
    )


def _build_task_user_prompt(task: PdfTask, parsed: PdfParseResult, source_text: str) -> str:
    return (
        f"Файл: {Path(parsed.source_path).name}\n"
        f"Страниц в PDF: {parsed.page_count}\n"
        f"Сценарий: {task}\n\n"
        f"Извлечённый текст документа:\n\n{source_text}\n\n"
        "Требования:\n"
        "- Не выдумывай отсутствующие факты.\n"
        "- Если реквизит, сумма, срок или дата не найдены — так и напиши.\n"
        "- Для claim_response draft_reply должен быть официальным ответом на русском.\n"
        "- Для остальных задач draft_reply можно оставить пустой строкой.\n"
    )


def parse_llm_json_response(raw_text: str) -> dict[str, Any]:
    try:
        return parse_json_object(raw_text)
    except Exception:
        repaired = _repair_minor_json_issues(raw_text)
        if repaired == raw_text:
            raise
        return parse_json_object(repaired)


def extract_structured_claim_response(raw_text: str) -> dict[str, Any]:
    payload = parse_llm_json_response(raw_text)
    summary = _normalize_text_field(payload.get("summary"))
    facts_src = payload.get("extracted_facts")
    facts = facts_src if isinstance(facts_src, dict) else {}

    claim_amounts = _normalize_list_field(
        facts.get("claim_amounts"),
        fallback=facts.get("amounts"),
    )
    dates = _normalize_list_field(facts.get("dates"))
    referenced_documents = _normalize_list_field(
        facts.get("referenced_documents"),
        fallback=facts.get("document_refs"),
    )
    legal_risks = _normalize_list_field(
        facts.get("legal_risks"),
        fallback=facts.get("risks"),
    )
    missing_information = _normalize_list_field(facts.get("missing_information"))

    normalized_facts = {
        "sender": _normalize_text_field(facts.get("sender")),
        "recipient": _normalize_text_field(facts.get("recipient")),
        "claim_subject": _normalize_text_field(
            facts.get("claim_subject"),
            fallback=facts.get("document_type"),
        ),
        "claim_amounts": claim_amounts,
        "dates": dates,
        "referenced_documents": referenced_documents,
        "response_deadline": _normalize_text_field(
            facts.get("response_deadline"),
            fallback=_first_list_item(facts.get("deadlines")),
        ),
        "recipient_position": _normalize_text_field(
            facts.get("recipient_position"),
            fallback=facts.get("position"),
        ),
        "legal_risks": legal_risks,
        "missing_information": missing_information,
    }

    _ensure_claim_missing_information(normalized_facts)
    return {
        "summary": summary,
        "extracted_facts": normalized_facts,
        "draft_reply": _normalize_text_field(payload.get("draft_reply")),
    }


async def generate_claim_reply_from_facts(
    structured_claim_response: dict[str, Any],
    *,
    client: httpx.AsyncClient,
    reply_mode: ClaimReplyMode = "auto",
    chat_func: Any = None,
) -> str:
    summary = _normalize_text_field(structured_claim_response.get("summary"))
    facts = structured_claim_response.get("extracted_facts")
    if not isinstance(facts, dict):
        raise PdfDocumentError("structured claim response не содержит extracted_facts")

    effective_mode = resolve_claim_reply_mode(facts, requested_mode=reply_mode)
    conservative = effective_mode == "request_documents" and _claim_reply_should_be_conservative(facts)
    user_prompt = _build_claim_reply_user_prompt(
        summary,
        facts,
        requested_mode=reply_mode,
        effective_mode=effective_mode,
        conservative=conservative,
    )
    reply = await (chat_func or chat_raw)(
        client=client,
        system=_CLAIM_REPLY_SYSTEM,
        user=user_prompt,
    )
    text = str(reply or "").strip()
    if not text:
        raise PdfDocumentError("Второй проход не вернул draft_reply")
    return text


def resolve_claim_reply_mode(
    facts: dict[str, Any],
    *,
    requested_mode: ClaimReplyMode,
) -> str:
    if requested_mode != "auto":
        return requested_mode
    if _claim_reply_should_be_conservative(facts):
        return "request_documents"
    return "neutral"


def _normalize_analysis_payload(payload: dict[str, Any]) -> dict[str, Any]:
    summary = str(payload.get("summary") or "").strip() or "n/a"
    facts = payload.get("extracted_facts")
    if not isinstance(facts, dict):
        facts = {"value": facts} if facts else {}
    draft_reply = str(payload.get("draft_reply") or "").strip()
    return {
        "summary": summary,
        "extracted_facts": json.loads(json.dumps(facts, ensure_ascii=False)),
        "draft_reply": draft_reply,
    }


def _repair_minor_json_issues(raw_text: str) -> str:
    repaired = raw_text.strip().replace("\ufeff", "")
    repaired = repaired.replace("“", '"').replace("”", '"')
    repaired = repaired.replace("‘", "'").replace("’", "'")
    repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
    repaired = re.sub(r"\bNone\b", "null", repaired)
    repaired = re.sub(r"\bTrue\b", "true", repaired)
    repaired = re.sub(r"\bFalse\b", "false", repaired)
    repaired = re.sub(r"([{\s,])'([^']+?)'\s*:", r'\1"\2":', repaired)
    repaired = re.sub(r':\s*\'([^\']*?)\'(\s*[,}])', r': "\1"\2', repaired)
    return repaired


def _normalize_text_field(value: Any, *, fallback: Any = None) -> str:
    candidate = value if value not in (None, "") else fallback
    if isinstance(candidate, list):
        candidate = _first_list_item(candidate)
    text = str(candidate or "").strip()
    return text if text else _UNKNOWN


def _normalize_list_field(value: Any, *, fallback: Any = None) -> list[str]:
    candidate = value if value not in (None, "", []) else fallback
    if candidate is None:
        return []
    if isinstance(candidate, list):
        return [str(item).strip() for item in candidate if str(item).strip()]
    text = str(candidate).strip()
    return [text] if text else []


def _first_list_item(value: Any) -> Any:
    if isinstance(value, list) and value:
        return value[0]
    return value


def _ensure_claim_missing_information(facts: dict[str, Any]) -> None:
    missing = set(facts.get("missing_information") or [])
    if facts["sender"] == _UNKNOWN:
        missing.add("sender")
    if facts["recipient"] == _UNKNOWN:
        missing.add("recipient")
    if facts["claim_subject"] == _UNKNOWN:
        missing.add("claim_subject")
    if not facts["claim_amounts"]:
        missing.add("claim_amounts")
    if not facts["dates"]:
        missing.add("dates")
    if not facts["referenced_documents"]:
        missing.add("referenced_documents")
    if facts["response_deadline"] == _UNKNOWN:
        missing.add("response_deadline")
    if facts["recipient_position"] == _UNKNOWN:
        missing.add("recipient_position")
    facts["missing_information"] = sorted(missing)


def _claim_reply_should_be_conservative(facts: dict[str, Any]) -> bool:
    return (
        facts.get("sender") == _UNKNOWN
        or facts.get("recipient") == _UNKNOWN
        or facts.get("claim_subject") == _UNKNOWN
        or not facts.get("claim_amounts")
        or not facts.get("dates")
    )


def _build_claim_reply_user_prompt(
    summary: str,
    facts: dict[str, Any],
    *,
    requested_mode: ClaimReplyMode,
    effective_mode: str,
    conservative: bool,
) -> str:
    guidance = (
        "Режим conservative: не признавай долг, не подтверждай факты категорично, "
        "используй формулировки о рассмотрении материалов и запросе подтверждающих документов."
        if conservative
        else
        _CLAIM_REPLY_MODE_GUIDANCE.get(
            effective_mode,
            "Подготовь официальный ответ без выдумывания фактов.",
        )
    )
    return (
        f"Сценарий: claim_response_second_pass\n"
        f"reply_mode_requested={requested_mode}\n"
        f"reply_mode_effective={effective_mode}\n"
        f"summary={summary}\n\n"
        f"extracted_facts=\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
        f"Требования:\n"
        f"- Используй только summary и extracted_facts.\n"
        f"- {guidance}\n"
        f"- Если данных недостаточно, прямо укажи это в нейтральной деловой форме.\n"
        f"- Не добавляй отсутствующие суммы, даты, реквизиты и ссылки на документы.\n"
    )
