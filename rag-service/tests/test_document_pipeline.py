from __future__ import annotations

import importlib.util
import json
import shutil
import uuid
import zipfile
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.services import document_pipeline, pdf_pipeline
from app.services.document_pipeline import (
    DocumentPipelineError,
    ParsedDocument,
    ParsedDocumentBlock,
    assess_extraction_quality,
    analyze_document,
    build_artifact_base_name,
    build_run_id,
    compute_file_sha256,
    detect_document_type,
    extract_text_from_docx,
    extract_text_from_image,
    extract_text_from_txt,
    extract_text_from_document,
)


@pytest.fixture
def work_dir() -> Path:
    root = Path(__file__).resolve().parents[2] / "_pytest_document_pipeline"
    root.mkdir(exist_ok=True)
    path = root / uuid.uuid4().hex
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _load_document_analyze_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "document_analyze.py"
    spec = importlib.util.spec_from_file_location("document_analyze_script", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_docx(path: Path) -> None:
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
      <w:body>
        <w:p><w:r><w:t>Претензия по договору.</w:t></w:r></w:p>
        <w:p><w:r><w:t>Отправитель: ООО Ромашка.</w:t></w:r></w:p>
        <w:tbl>
          <w:tr>
            <w:tc><w:p><w:r><w:t>Сумма</w:t></w:r></w:p></w:tc>
            <w:tc><w:p><w:r><w:t>120 000 руб.</w:t></w:r></w:p></w:tc>
          </w:tr>
        </w:tbl>
      </w:body>
    </w:document>"""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", document_xml)


def _write_scan_only_pdf(path: Path, text: str) -> None:
    img = Image.new("RGB", (1200, 1600), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((80, 120), text, fill="black")
    img.save(path, "PDF")


def _parsed_stub(file_type: str, extraction_method: str) -> ParsedDocument:
    text = (
        "Претензия по оплате по договору поставки. "
        "Отправитель: ООО Ромашка. Получатель: ООО Вектор."
    )
    return ParsedDocument(
        source_path=f"C:/tmp/sample.{file_type}",
        file_type=file_type,  # type: ignore[arg-type]
        file_size_bytes=100,
        text=text,
        blocks=[ParsedDocumentBlock(index=1, text=text, page_number=1)],
        warnings=[],
        extraction_method=extraction_method,
        page_count=1,
    )


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("x.pdf", "pdf"),
        ("x.docx", "docx"),
        ("x.txt", "txt"),
        ("x.jpg", "image"),
        ("x.jpeg", "image"),
        ("x.png", "image"),
        ("x.webp", "image"),
    ],
)
def test_detect_document_type(name: str, expected: str):
    assert detect_document_type(name) == expected


def test_docx_extraction_success(work_dir: Path):
    path = work_dir / "pretension.docx"
    _write_docx(path)

    parsed = extract_text_from_docx(path)

    assert parsed.file_type == "docx"
    assert parsed.extraction_method == "docx"
    assert "ООО Ромашка" in parsed.text
    assert "120 000 руб." in parsed.text


def test_txt_extraction_utf8_success(work_dir: Path):
    path = work_dir / "letter.txt"
    path.write_text("Претензия\nСумма: 120 000 руб.", encoding="utf-8")

    parsed = extract_text_from_txt(path)

    assert parsed.file_type == "txt"
    assert parsed.extraction_method == "plain_text"
    assert "120 000 руб." in parsed.text
    assert parsed.warnings == []
    assert parsed.extraction_quality in {"high", "medium"}


def test_txt_extraction_cp1251_fallback(work_dir: Path):
    path = work_dir / "letter-cp1251.txt"
    path.write_bytes("Претензия по оплате".encode("cp1251"))

    parsed = extract_text_from_txt(path)

    assert parsed.text == "Претензия по оплате"
    assert parsed.warnings == ["encoding_cp1251"]


def test_empty_text_quality_is_low():
    parsed = ParsedDocument(
        source_path="C:/tmp/empty.txt",
        file_type="txt",
        file_size_bytes=0,
        text="",
        blocks=[],
        warnings=[],
        extraction_method="plain_text",
        page_count=1,
    )

    assessed = assess_extraction_quality(parsed)

    assert assessed.extraction_quality == "low"
    assert "empty_text" in assessed.quality_reasons


def test_short_noisy_ocr_text_quality_is_low():
    parsed = ParsedDocument(
        source_path="C:/tmp/scan.png",
        file_type="image",
        file_size_bytes=100,
        text="12 @@ ??",
        blocks=[ParsedDocumentBlock(index=1, text="12 @@ ??", kind="image")],
        warnings=["low_ocr_text"],
        extraction_method="ocr",
        page_count=1,
    )

    assessed = assess_extraction_quality(parsed)

    assert assessed.extraction_quality == "low"
    assert "ocr_source" in assessed.quality_reasons


def test_normal_extracted_text_quality_is_high():
    assessed = assess_extraction_quality(_parsed_stub("txt", "plain_text"))

    assert assessed.extraction_quality in {"high", "medium"}
    assert assessed.text_char_count > 0
    assert assessed.non_whitespace_char_count > 0


def test_broken_docx_gives_clear_error(work_dir: Path):
    path = work_dir / "broken.docx"
    path.write_bytes(b"not-a-real-docx")

    with pytest.raises(DocumentPipelineError, match="Битый DOCX|Не удалось открыть DOCX"):
        extract_text_from_docx(path)


def test_image_extractor_without_ocr_backend_gives_clear_error(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    path = work_dir / "scan.png"
    Image.new("RGB", (16, 16), color="white").save(path)
    monkeypatch.setattr(document_pipeline, "_load_ocr_backend", lambda: (_ for _ in ()).throw(
        DocumentPipelineError("OCR backend unavailable: pytesseract not installed or not configured.")
    ))

    with pytest.raises(DocumentPipelineError, match="OCR backend unavailable"):
        extract_text_from_image(path)


def test_extract_text_from_document_routes_correctly(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(document_pipeline, "extract_text_from_pdf", lambda *a, **k: _parsed_stub("pdf", "pypdf"))
    monkeypatch.setattr(document_pipeline, "extract_text_from_docx", lambda *a, **k: _parsed_stub("docx", "docx"))
    monkeypatch.setattr(document_pipeline, "extract_text_from_txt", lambda *a, **k: _parsed_stub("txt", "plain_text"))
    monkeypatch.setattr(document_pipeline, "extract_text_from_image", lambda *a, **k: _parsed_stub("image", "ocr"))

    assert extract_text_from_document("a.pdf").file_type == "pdf"
    assert extract_text_from_document("a.docx").file_type == "docx"
    assert extract_text_from_document("a.txt").file_type == "txt"
    assert extract_text_from_document("a.jpg").file_type == "image"


def test_scan_only_pdf_without_text_layer_returns_clear_status(work_dir: Path):
    path = work_dir / "scan.pdf"
    _write_scan_only_pdf(path, "Претензия по оплате 120 000 руб.")

    with pytest.raises(DocumentPipelineError) as exc_info:
        extract_text_from_document(path)

    err = exc_info.value
    assert "текстовый слой" in str(err).lower()
    assert "пуст" not in str(err).lower()
    assert getattr(err, "code", None) == "no_text_layer_but_pages_present"
    assert err.debug_info["source_kind"] == "pdf"
    assert err.debug_info["text_layer_found"] is False
    assert err.debug_info["pages_present"] is True
    assert err.debug_info["pages_count"] == 1
    assert err.debug_info["fallback_used"] == "tech_notice"
    assert err.debug_info["extraction_status"] == "no_text_layer_but_pages_present"


def test_scan_only_pdf_with_ocr_flag_still_returns_honest_ocr_needed_message(work_dir: Path):
    path = work_dir / "scan-ocr.pdf"
    _write_scan_only_pdf(path, "Скан претензии")

    with pytest.raises(DocumentPipelineError) as exc_info:
        extract_text_from_document(path, enable_ocr_fallback=True)

    err = exc_info.value
    assert "ocr fallback requested" in str(err).lower()
    assert getattr(err, "code", None) == "no_text_layer_but_pages_present"


@pytest.mark.asyncio
async def test_analyze_document_claim_response_contract_stable_for_txt(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    path = work_dir / "letter.txt"
    path.write_text(
        "Претензия. Отправитель: ООО Ромашка. Получатель: ООО Вектор. "
        "Требование: оплатить 120 000 руб. Срок ответа: 10 дней.",
        encoding="utf-8",
    )

    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        if "готовишь официальный ответ на претензию" in system:
            return "Уважаемые коллеги, просим учесть изложенную позицию и направить подтверждающие документы."
        return (
            '{"summary":"Претензия по оплате",'
            '"extracted_facts":{"sender":"ООО Ромашка","recipient":"ООО Вектор","claim_subject":"неоплата",'
            '"claim_amounts":["120 000 руб."],"dates":["01.03.2026"],"referenced_documents":["договор №15"],'
            '"response_deadline":"10 дней","recipient_position":"заказчик","legal_risks":[],"missing_information":[]},'
            '"draft_reply":"черновик"}'
        )

    monkeypatch.setattr(document_pipeline, "chat_raw", fake_chat_raw)

    result = await analyze_document(path, task="claim_response", output_dir=work_dir / "texts")

    assert result.file_type == "txt"
    assert result.extraction_method == "plain_text"
    assert result.extracted_facts["sender"] == "ООО Ромашка"
    assert result.reply_mode_requested == "auto"
    assert result.reply_mode_effective == "neutral"
    assert "Уважаемые коллеги" in result.draft_reply
    assert any("claim_response_second_pass" in user for _, user in calls)
    assert result.extraction_quality in {"high", "medium"}
    assert Path(result.analysis_path).is_file()


@pytest.mark.asyncio
async def test_claim_response_low_quality_path_remains_safe_and_conservative(
    work_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    path = work_dir / "scan.txt"
    path.write_text("12 @@ ??", encoding="utf-8")

    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        if "готовишь официальный ответ на претензию" in system:
            return "Просим направить подтверждающие документы и материалы для оценки изложенных требований."
        return (
            '{"summary":"Текст извлечён частично",'
            '"extracted_facts":{"sender":"unknown","recipient":"unknown","claim_subject":"unknown",'
            '"claim_amounts":[],"dates":[],"referenced_documents":[],"response_deadline":"unknown",'
            '"recipient_position":"unknown","legal_risks":[],"missing_information":[]},'
            '"draft_reply":"черновик"}'
        )

    monkeypatch.setattr(document_pipeline, "chat_raw", fake_chat_raw)

    result = await analyze_document(path, task="claim_response", output_dir=work_dir / "texts")

    assert result.extraction_quality == "low"
    assert result.reply_mode_effective == "request_documents"
    assert "low_extraction_quality" in result.warnings
    assert "claim_response_based_on_low_quality_extraction" in result.warnings
    assert "подтверждающие документы" in result.draft_reply


@pytest.mark.asyncio
async def test_analysis_json_saved_after_summary_task(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    path = work_dir / "letter.txt"
    path.write_text("Краткое письмо по договору поставки.", encoding="utf-8")

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        return '{"summary":"Краткая сводка","extracted_facts":{"document_type":"letter"},"draft_reply":""}'

    monkeypatch.setattr(document_pipeline, "chat_raw", fake_chat_raw)

    result = await analyze_document(path, task="summary", output_dir=work_dir / "texts")
    saved = Path(result.analysis_path)

    assert saved.is_file()
    payload = json.loads(saved.read_text(encoding="utf-8"))
    assert payload["task"] == "summary"
    assert payload["summary"] == "Краткая сводка"
    assert payload["text_saved_path"] == result.text_path
    assert payload["analysis_saved_path"] == result.analysis_path


@pytest.mark.asyncio
async def test_analysis_json_saved_after_claim_response_task(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    path = work_dir / "claim.txt"
    path.write_text("Претензия. Отправитель: ООО Ромашка. Получатель: ООО Вектор.", encoding="utf-8")

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        if "готовишь официальный ответ на претензию" in system:
            return "Уважаемые коллеги, сообщаем позицию по претензии."
        return (
            '{"summary":"Претензия",'
            '"extracted_facts":{"sender":"ООО Ромашка","recipient":"ООО Вектор","claim_subject":"unknown",'
            '"claim_amounts":[],"dates":[],"referenced_documents":[],"response_deadline":"unknown",'
            '"recipient_position":"unknown","legal_risks":[],"missing_information":[]},'
            '"draft_reply":"черновик"}'
        )

    monkeypatch.setattr(document_pipeline, "chat_raw", fake_chat_raw)

    result = await analyze_document(path, task="claim_response", output_dir=work_dir / "texts")
    payload = json.loads(Path(result.analysis_path).read_text(encoding="utf-8"))

    assert payload["task"] == "claim_response"
    assert payload["reply_mode_requested"] == "auto"
    assert payload["reply_mode_effective"] in {"neutral", "request_documents"}
    assert payload["draft_reply"] == result.draft_reply


@pytest.mark.asyncio
async def test_saved_analysis_contains_quality_metadata(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    path = work_dir / "letter.txt"
    path.write_text("Краткое письмо по договору поставки.", encoding="utf-8")

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        return '{"summary":"Краткая сводка","extracted_facts":{"document_type":"letter"},"draft_reply":""}'

    monkeypatch.setattr(document_pipeline, "chat_raw", fake_chat_raw)

    result = await analyze_document(path, task="summary", output_dir=work_dir / "texts")
    payload = json.loads(Path(result.analysis_path).read_text(encoding="utf-8"))

    assert payload["extraction_quality"] == result.extraction_quality
    assert payload["quality_reasons"] == result.quality_reasons
    assert payload["extraction_status"] == result.extraction_status
    assert payload["fallback_used"] == result.fallback_used
    assert payload["pages_present"] == result.pages_present
    assert payload["text_char_count"] == result.text_char_count
    assert payload["non_whitespace_char_count"] == result.non_whitespace_char_count
    assert payload["created_at_utc"]


@pytest.mark.asyncio
async def test_saved_analysis_contains_reply_mode_fields(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    path = work_dir / "claim.txt"
    path.write_text("Претензия по оплате.", encoding="utf-8")

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        if "готовишь официальный ответ на претензию" in system:
            return "Просим направить подтверждающие документы."
        return (
            '{"summary":"Претензия",'
            '"extracted_facts":{"sender":"unknown","recipient":"unknown","claim_subject":"unknown",'
            '"claim_amounts":[],"dates":[],"referenced_documents":[],"response_deadline":"unknown",'
            '"recipient_position":"unknown","legal_risks":[],"missing_information":[]},'
            '"draft_reply":"черновик"}'
        )

    monkeypatch.setattr(document_pipeline, "chat_raw", fake_chat_raw)

    result = await analyze_document(path, task="claim_response", output_dir=work_dir / "texts")
    payload = json.loads(Path(result.analysis_path).read_text(encoding="utf-8"))

    assert payload["reply_mode_requested"] == "auto"
    assert payload["reply_mode_effective"] == result.reply_mode_effective
    assert payload["warnings"] == result.warnings


@pytest.mark.asyncio
async def test_repeated_runs_do_not_overwrite_artifacts(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    path = work_dir / "letter.txt"
    path.write_text("Краткое письмо по договору поставки.", encoding="utf-8")

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        return '{"summary":"Краткая сводка","extracted_facts":{"document_type":"letter"},"draft_reply":""}'

    monkeypatch.setattr(document_pipeline, "chat_raw", fake_chat_raw)

    first = await analyze_document(path, task="summary", output_dir=work_dir / "texts")
    second = await analyze_document(path, task="summary", output_dir=work_dir / "texts")

    assert first.text_path != second.text_path
    assert first.analysis_path != second.analysis_path
    assert Path(first.text_path).is_file()
    assert Path(second.text_path).is_file()
    assert Path(first.analysis_path).is_file()
    assert Path(second.analysis_path).is_file()


@pytest.mark.asyncio
async def test_analysis_json_contains_run_id_and_source_hash(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    path = work_dir / "letter.txt"
    path.write_text("Краткое письмо по договору поставки.", encoding="utf-8")

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        return '{"summary":"Краткая сводка","extracted_facts":{"document_type":"letter"},"draft_reply":""}'

    monkeypatch.setattr(document_pipeline, "chat_raw", fake_chat_raw)

    result = await analyze_document(path, task="summary", output_dir=work_dir / "texts")
    payload = json.loads(Path(result.analysis_path).read_text(encoding="utf-8"))

    assert payload["run_id"] == result.run_id
    assert payload["source_file_hash_sha256"] == compute_file_sha256(path)
    assert payload["source_file_name"] == "letter.txt"
    assert payload["model_used"]


@pytest.mark.asyncio
async def test_filename_includes_safe_deterministic_identity(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    path = work_dir / "Письмо №1!.txt"
    path.write_text("Краткое письмо по договору поставки.", encoding="utf-8")

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        return '{"summary":"Краткая сводка","extracted_facts":{"document_type":"letter"},"draft_reply":""}'

    monkeypatch.setattr(document_pipeline, "chat_raw", fake_chat_raw)

    result = await analyze_document(path, task="summary", output_dir=work_dir / "texts")
    text_name = Path(result.text_path).name

    assert ".summary." in text_name
    assert result.run_id in text_name
    assert "!" not in text_name
    assert " " not in text_name


def test_run_helpers_build_stable_identity():
    run_id = build_run_id("2026-04-04T15:30:12.123456+00:00", "ab12cd34ef56")
    base = build_artifact_base_name(Path("C:/tmp/Письмо №1!.txt"), task="summary", run_id=run_id)

    assert run_id.startswith("20260404T153012123456Z_")
    assert base.endswith(f".summary.{run_id}")
    assert "!" not in base
    assert " " not in base


@pytest.mark.asyncio
async def test_old_pdf_path_still_works(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    from fpdf import FPDF

    font = Path(__file__).resolve().parents[1] / "app" / "assets" / "fonts" / "DejaVuSans.ttf"
    path = work_dir / "claim.pdf"
    pdf_doc = FPDF()
    pdf_doc.set_auto_page_break(auto=True, margin=12)
    pdf_doc.add_font("DejaVuSans", "", str(font))
    pdf_doc.add_page()
    pdf_doc.set_font("DejaVuSans", "", 12)
    pdf_doc.multi_cell(0, 8, "Претензия. Отправитель: ООО Ромашка. Получатель: ООО Вектор.")
    out = pdf_doc.output()
    path.write_bytes(out.encode("latin-1") if isinstance(out, str) else bytes(out))

    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        if "готовишь официальный ответ на претензию" in system:
            return "Уважаемые коллеги, сообщаем позицию по претензии."
        return (
            '{"summary":"Претензия",'
            '"extracted_facts":{"sender":"ООО Ромашка","recipient":"ООО Вектор","claim_subject":"unknown",'
            '"claim_amounts":[],"dates":[],"referenced_documents":[],"response_deadline":"unknown",'
            '"recipient_position":"unknown","legal_risks":[],"missing_information":[]},'
            '"draft_reply":"черновик"}'
        )

    monkeypatch.setattr(pdf_pipeline, "chat_raw", fake_chat_raw)

    result = await pdf_pipeline.analyze_pdf_document(path, task="claim_response", output_dir=work_dir / "pdf-text")

    assert result.summary == "Претензия"
    assert result.extracted_facts["sender"] == "ООО Ромашка"
    assert result.draft_reply == "Уважаемые коллеги, сообщаем позицию по претензии."
    assert len(calls) >= 2


def test_document_cli_json_works(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    module = _load_document_analyze_module()

    async def fake_analyze(*args, **kwargs):
        return document_pipeline.DocumentAnalysisResult(
            task="summary",
            run_id="20260404T153012123456Z_ab12cd34",
            created_at_utc="2026-04-04T15:30:12.123456+00:00",
            source_file_name="letter.txt",
            source_file_hash_sha256="ab12cd34ef56",
            model_used="qwen2.5:14b",
            source_path="C:/tmp/letter.txt",
            file_type="txt",
            extraction_method="plain_text",
            extraction_quality="high",
            quality_reasons=[],
            text_char_count=20,
            non_whitespace_char_count=18,
            suspicious_text=False,
            ocr_used=False,
            extraction_status="text_extracted",
            text_layer_found=None,
            pages_present=True,
            fallback_used="none",
            user_safe_reason=None,
            text_path="C:/tmp/letter.txt.txt",
            analysis_path="C:/tmp/letter.analysis.json",
            page_count=1,
            block_count=1,
            chunk_count=1,
            summary="Краткая сводка",
            extracted_facts={"document_type": "letter"},
            draft_reply="",
            warnings=[],
            raw_response={
                "summary": "Краткая сводка",
                "extracted_facts": {"document_type": "letter"},
                "draft_reply": "",
                "run_id": "20260404T153012123456Z_ab12cd34",
                "text_saved_path": "C:/tmp/letter.txt.txt",
                "file_type": "txt",
                "extraction_method": "plain_text",
                "extraction_quality": "high",
                "quality_reasons": [],
                "extraction_status": "text_extracted",
                "text_layer_found": None,
                "pages_present": True,
                "pages_count": 1,
                "fallback_used": "none",
                "user_safe_reason": None,
                "analysis_saved_path": "C:/tmp/letter.analysis.json",
            },
        )

    monkeypatch.setattr(module, "analyze_document", fake_analyze)

    rc = module.main(["--file", "letter.txt", "--task", "summary", "--json"])
    out = capsys.readouterr().out

    assert rc == 0
    parsed = json.loads(out)
    assert parsed["summary"] == "Краткая сводка"
    assert parsed["file_type"] == "txt"
    assert parsed["extraction_quality"] == "high"
    assert parsed["extraction_status"] == "text_extracted"
    assert parsed["fallback_used"] == "none"
    assert parsed["analysis_saved_path"] == "C:/tmp/letter.analysis.json"
    assert parsed["run_id"] == "20260404T153012123456Z_ab12cd34"
    assert parsed["text_saved_path"] == "C:/tmp/letter.txt.txt"


def test_document_cli_output_includes_extraction_quality(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    module = _load_document_analyze_module()

    async def fake_analyze(*args, **kwargs):
        return document_pipeline.DocumentAnalysisResult(
            task="summary",
            run_id="20260404T153012123456Z_ab12cd34",
            created_at_utc="2026-04-04T15:30:12.123456+00:00",
            source_file_name="letter.txt",
            source_file_hash_sha256="ab12cd34ef56",
            model_used="qwen2.5:14b",
            source_path="C:/tmp/letter.txt",
            file_type="txt",
            extraction_method="plain_text",
            extraction_quality="medium",
            quality_reasons=["short_text"],
            text_char_count=30,
            non_whitespace_char_count=26,
            suspicious_text=False,
            ocr_used=False,
            extraction_status="text_extracted",
            text_layer_found=None,
            pages_present=True,
            fallback_used="none",
            user_safe_reason=None,
            text_path="C:/tmp/letter.txt.txt",
            analysis_path="C:/tmp/letter.analysis.json",
            page_count=1,
            block_count=1,
            chunk_count=1,
            summary="Краткая сводка",
            extracted_facts={"document_type": "letter"},
            draft_reply="",
            warnings=[],
            raw_response={
                "summary": "Краткая сводка",
                "extracted_facts": {"document_type": "letter"},
                "draft_reply": "",
                "run_id": "20260404T153012123456Z_ab12cd34",
                "text_saved_path": "C:/tmp/letter.txt.txt",
                "file_type": "txt",
                "extraction_method": "plain_text",
                "extraction_quality": "medium",
                "quality_reasons": ["short_text"],
                "extraction_status": "text_extracted",
                "text_layer_found": None,
                "pages_present": True,
                "pages_count": 1,
                "fallback_used": "none",
                "user_safe_reason": None,
                "analysis_saved_path": "C:/tmp/letter.analysis.json",
            },
        )

    monkeypatch.setattr(module, "analyze_document", fake_analyze)

    rc = module.main(["--file", "letter.txt", "--task", "summary"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "extraction_quality=medium" in out
    assert "extraction_status=text_extracted" in out
    assert "fallback_used=none" in out
    assert "quality_reasons=short_text" in out
    assert "analysis_saved=C:/tmp/letter.analysis.json" in out


def test_backward_parsing_of_analysis_artifact_is_valid_json(work_dir: Path):
    payload = {
        "run_id": "20260404T153012123456Z_ab12cd34",
        "created_at_utc": "2026-04-04T15:30:12.123456+00:00",
        "source_file_name": "letter.txt",
        "source_file_hash_sha256": "ab12cd34ef56",
        "task": "summary",
        "model_used": "qwen2.5:14b",
        "summary": "Краткая сводка",
        "extracted_facts": {"document_type": "letter"},
        "draft_reply": "",
        "text_saved_path": "C:/tmp/letter.txt.txt",
        "analysis_saved_path": "C:/tmp/letter.analysis.json",
    }
    path = work_dir / "letter.analysis.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    parsed = json.loads(path.read_text(encoding="utf-8"))

    assert parsed["run_id"] == payload["run_id"]
    assert parsed["summary"] == payload["summary"]
