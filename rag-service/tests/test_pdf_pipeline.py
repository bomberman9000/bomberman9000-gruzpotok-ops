from __future__ import annotations

import importlib.util
import json
import shutil
import uuid
from pathlib import Path

import pytest
from fpdf import FPDF
from PIL import Image, ImageDraw

from app.services import pdf_pipeline
from app.services.pdf_pipeline import (
    PdfDocumentError,
    extract_structured_claim_response,
    generate_claim_reply_from_facts,
    build_pdf_chunks,
    extract_text_from_pdf,
    analyze_pdf_document,
    parse_llm_json_response,
    resolve_claim_reply_mode,
)


_FONT_NAME = "DejaVuSans"


@pytest.fixture
def work_dir() -> Path:
    root = Path(__file__).resolve().parents[2] / "_pytest_pdf_pipeline"
    root.mkdir(exist_ok=True)
    path = root / uuid.uuid4().hex
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _font_path() -> Path:
    return Path(__file__).resolve().parents[1] / "app" / "assets" / "fonts" / "DejaVuSans.ttf"


def _write_pdf(path: Path, pages: list[str]) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_font(_FONT_NAME, "", str(_font_path()))
    for page_text in pages:
        pdf.add_page()
        pdf.set_font(_FONT_NAME, "", 12)
        pdf.multi_cell(0, 8, page_text)
    raw = pdf.output()
    path.write_bytes(raw.encode("latin-1") if isinstance(raw, str) else bytes(raw))


def _write_scan_only_pdf(path: Path, text: str) -> None:
    img = Image.new("RGB", (1200, 1600), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((80, 120), text, fill="black")
    img.save(path, "PDF")


def _load_pdf_analyze_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "pdf_analyze.py"
    spec = importlib.util.spec_from_file_location("pdf_analyze_script", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_text_from_pdf_reads_text_pdf(work_dir: Path):
    pdf_path = work_dir / "claim.pdf"
    _write_pdf(
        pdf_path,
        [
            "Претензия по договору перевозки.\n"
            "Отправитель: ООО Ромашка.\n"
            "Сумма требований: 120 000 руб.\n"
            "Срок ответа: 10 дней."
        ],
    )

    result = extract_text_from_pdf(pdf_path)

    assert result.page_count == 1
    assert "ООО Ромашка" in result.text
    assert "120 000 руб." in result.text
    assert result.warnings == []


def test_extract_text_from_pdf_reads_multipage_pdf(work_dir: Path):
    pdf_path = work_dir / "multi.pdf"
    _write_pdf(
        pdf_path,
        [
            "Страница 1.\nДоговор поставки.\nДата: 01.04.2026.",
            "Страница 2.\nОплата в течение 5 банковских дней.",
        ],
    )

    result = extract_text_from_pdf(pdf_path)

    assert result.page_count == 2
    assert len(result.pages) == 2
    assert result.pages[0].page_number == 1
    assert "Договор поставки" in result.pages[0].text
    assert "5 банковских дней" in result.pages[1].text


def test_extract_text_from_pdf_scan_only_pdf_returns_clear_non_empty_reason(work_dir: Path):
    pdf_path = work_dir / "scan.pdf"
    _write_scan_only_pdf(pdf_path, "Претензия по договору перевозки")

    with pytest.raises(PdfDocumentError) as exc_info:
        extract_text_from_pdf(pdf_path)

    err = exc_info.value
    assert "текстовый слой" in str(err).lower()
    assert "пуст" not in str(err).lower()
    assert err.code == "no_text_layer_but_pages_present"
    assert err.debug_info["pages_present"] is True
    assert err.debug_info["pages_count"] == 1


def test_extract_text_from_pdf_bad_pdf_error(work_dir: Path):
    pdf_path = work_dir / "broken.pdf"
    pdf_path.write_bytes(b"not-a-real-pdf")

    with pytest.raises(PdfDocumentError, match="Битый|Не удалось открыть"):
        extract_text_from_pdf(pdf_path)


def test_build_pdf_chunks_stable(work_dir: Path):
    pdf_path = work_dir / "long.pdf"
    long_para = (
        "Настоящая претензия связана с просрочкой оплаты и нарушением условий договора. "
        "Просим в добровольном порядке погасить задолженность в размере 150 000 руб. "
        "и направить письменный ответ в течение 7 календарных дней. "
    ) * 8
    _write_pdf(pdf_path, [long_para, long_para])
    parsed = extract_text_from_pdf(pdf_path)

    chunks = build_pdf_chunks(parsed.pages, max_chars=700, overlap=120)

    assert len(chunks) >= 3
    assert chunks[0].start_page == 1
    assert chunks[-1].end_page == 2
    assert all(chunk.text.strip() for chunk in chunks)
    assert all(len(chunk.text) <= 700 for chunk in chunks)


def test_parse_llm_json_response_valid_json():
    raw = '{"summary":"ok","extracted_facts":{"sender":"A"},"draft_reply":"B"}'

    out = parse_llm_json_response(raw)

    assert out["summary"] == "ok"
    assert out["extracted_facts"]["sender"] == "A"


def test_parse_llm_json_response_markdown_fenced_json():
    raw = """```json
    {
      "summary": "ok",
      "extracted_facts": {"sender": "ООО Ромашка"},
      "draft_reply": "reply"
    }
    ```"""

    out = parse_llm_json_response(raw)

    assert out["extracted_facts"]["sender"] == "ООО Ромашка"


def test_parse_llm_json_response_slightly_malformed_repaired():
    raw = """{
      'summary': 'ok',
      'extracted_facts': {'sender': 'ООО Ромашка',},
      'draft_reply': 'reply',
    }"""

    out = parse_llm_json_response(raw)

    assert out["summary"] == "ok"
    assert out["extracted_facts"]["sender"] == "ООО Ромашка"


def test_parse_llm_json_response_unrecoverable_raises():
    raw = "summary=ok facts=broken"

    with pytest.raises(Exception):
        parse_llm_json_response(raw)


@pytest.mark.asyncio
async def test_analyze_pdf_document_claim_response_pipeline(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    pdf_path = work_dir / "claim_response.pdf"
    page_one = (
        "Претензия.\n"
        "Отправитель: ООО Ромашка.\n"
        "Получатель: ООО Вектор.\n"
        "Требование: оплатить 120 000 руб. по акту №7.\n"
        "Срок ответа: 10 дней.\n"
    ) * 4
    page_two = (
        "Основание: договор №15 от 01.03.2026.\n"
        "Оплата не поступила.\n"
        "Просим перечислить сумму и направить ответ.\n"
    ) * 4
    _write_pdf(pdf_path, [page_one, page_two])

    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        if "анализируешь только часть PDF-документа" in system:
            return "- стороны: ООО Ромашка / ООО Вектор\n- сумма: 120 000 руб.\n- срок: 10 дней"
        if "готовишь официальный ответ на претензию" in system:
            return "Уважаемые коллеги, по результатам рассмотрения сообщаем мотивированную позицию по претензии."
        return (
            '{"summary":"Претензия о взыскании 120 000 руб.",'
            '"extracted_facts":{"sender":"ООО Ромашка","recipient":"ООО Вектор","claim_subject":"взыскание задолженности",'
            '"claim_amounts":["120 000 руб."],"dates":["01.03.2026"],"referenced_documents":["договор №15","акт №7"],'
            '"response_deadline":"10 дней","recipient_position":"покупатель","legal_risks":["судебное взыскание"],"missing_information":[]},'
            '"draft_reply":"Черновик первого прохода."}'
        )

    monkeypatch.setattr(pdf_pipeline, "chat_raw", fake_chat_raw)

    result = await analyze_pdf_document(
        pdf_path,
        task="claim_response",
        output_dir=work_dir / "pdf-text",
        chunk_max_chars=500,
        chunk_overlap=80,
        direct_text_limit=300,
        reply_mode="auto",
    )

    assert result.summary == "Претензия о взыскании 120 000 руб."
    assert result.extracted_facts["sender"] == "ООО Ромашка"
    assert result.extracted_facts["recipient"] == "ООО Вектор"
    assert result.extracted_facts["claim_subject"] == "взыскание задолженности"
    assert result.extracted_facts["claim_amounts"] == ["120 000 руб."]
    assert result.extracted_facts["dates"] == ["01.03.2026"]
    assert result.extracted_facts["referenced_documents"] == ["договор №15", "акт №7"]
    assert result.extracted_facts["response_deadline"] == "10 дней"
    assert result.extracted_facts["recipient_position"] == "покупатель"
    assert result.extracted_facts["legal_risks"] == ["судебное взыскание"]
    assert result.extracted_facts["missing_information"] == []
    assert result.draft_reply == "Уважаемые коллеги, по результатам рассмотрения сообщаем мотивированную позицию по претензии."
    assert result.reply_mode_requested == "auto"
    assert result.reply_mode_effective == "neutral"
    assert Path(result.text_path).is_file()
    assert len(calls) >= 3
    assert any("Сценарий: claim_response" in user for _, user in calls)
    assert any("Верни только один JSON-объект" in system for system, _ in calls)
    assert any("готовишь официальный ответ на претензию" in system for system, _ in calls)


@pytest.mark.asyncio
async def test_second_pass_uses_structured_facts_not_raw_pdf_text(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        return "Уважаемые коллеги, просим направить подтверждающие документы."

    monkeypatch.setattr(pdf_pipeline, "chat_raw", fake_chat_raw)

    structured = {
        "summary": "Претензия по оплате 120 000 руб.",
        "extracted_facts": {
            "sender": "ООО Ромашка",
            "recipient": "ООО Вектор",
            "claim_subject": "неоплата по акту",
            "claim_amounts": ["120 000 руб."],
            "dates": ["01.03.2026"],
            "referenced_documents": ["договор №15"],
            "response_deadline": "10 дней",
            "recipient_position": "заказчик",
            "legal_risks": [],
            "missing_information": [],
        },
    }

    import httpx

    async with httpx.AsyncClient() as client:
        reply = await generate_claim_reply_from_facts(structured, client=client)

    assert reply.startswith("Уважаемые коллеги")
    assert len(calls) == 1
    system, user = calls[0]
    assert "готовишь официальный ответ на претензию" in system
    assert "extracted_facts=" in user
    assert "Извлечённый текст документа" not in user
    assert "сырой PDF" not in user


@pytest.mark.asyncio
async def test_conservative_reply_when_extracted_facts_incomplete(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        return "По результатам рассмотрения сообщаем, что для формирования позиции просим направить подтверждающие документы."

    monkeypatch.setattr(pdf_pipeline, "chat_raw", fake_chat_raw)

    structured = {
        "summary": "Претензия по оплате.",
        "extracted_facts": {
            "sender": "unknown",
            "recipient": "unknown",
            "claim_subject": "unknown",
            "claim_amounts": [],
            "dates": [],
            "referenced_documents": [],
            "response_deadline": "unknown",
            "recipient_position": "unknown",
            "legal_risks": [],
            "missing_information": ["sender", "recipient"],
        },
    }

    import httpx

    async with httpx.AsyncClient() as client:
        reply = await generate_claim_reply_from_facts(structured, client=client)

    assert "подтверждающие документы" in reply
    assert len(calls) == 1
    assert "reply_mode_requested=auto" in calls[0][1]
    assert "reply_mode_effective=request_documents" in calls[0][1]


@pytest.mark.asyncio
async def test_hallucination_guard_second_pass_prompt_does_not_include_unavailable_invented_fields(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        return "reply"

    monkeypatch.setattr(pdf_pipeline, "chat_raw", fake_chat_raw)

    structured = {
        "summary": "Претензия по оплате.",
        "extracted_facts": {
            "sender": "ООО Ромашка",
            "recipient": "ООО Вектор",
            "claim_subject": "unknown",
            "claim_amounts": [],
            "dates": [],
            "referenced_documents": [],
            "response_deadline": "unknown",
            "recipient_position": "unknown",
            "legal_risks": [],
            "missing_information": ["claim_subject", "claim_amounts"],
        },
    }

    import httpx

    async with httpx.AsyncClient() as client:
        await generate_claim_reply_from_facts(structured, client=client)

    prompt = calls[0][1]
    assert '"claim_subject": "unknown"' in prompt
    assert '"claim_amounts": []' in prompt
    assert "акт №999" not in prompt
    assert "ИНН" not in prompt


def test_extract_structured_claim_response_matches_required_schema():
    raw = json.dumps(
        {
            "summary": "Претензия по оплате",
            "extracted_facts": {
                "sender": "ООО Ромашка",
                "recipient": "ООО Вектор",
                "claim_subject": "неоплата по акту",
                "claim_amounts": ["120 000 руб."],
                "dates": ["01.03.2026"],
                "referenced_documents": ["договор №15"],
                "response_deadline": "10 дней",
                "recipient_position": "заказчик",
                "legal_risks": ["судебное взыскание"],
                "missing_information": [],
            },
            "draft_reply": "Проект ответа",
        },
        ensure_ascii=False,
    )

    out = extract_structured_claim_response(raw)

    assert sorted(out.keys()) == ["draft_reply", "extracted_facts", "summary"]
    assert sorted(out["extracted_facts"].keys()) == [
        "claim_amounts",
        "claim_subject",
        "dates",
        "legal_risks",
        "missing_information",
        "recipient",
        "recipient_position",
        "referenced_documents",
        "response_deadline",
        "sender",
    ]


def test_cli_json_returns_structured_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    module = _load_pdf_analyze_module()

    async def fake_analyze(*args, **kwargs):
        return type(
            "FakeDocAnalysis",
            (),
            {
                "task": "claim_response",
                "source_path": "C:/tmp/sample.pdf",
                "file_type": "pdf",
                "extraction_method": "pypdf",
                "extraction_quality": "high",
                "extraction_status": "text_extracted",
                "fallback_used": "none",
                "text_layer_found": True,
                "pages_present": True,
                "user_safe_reason": None,
                "text_path": "C:/tmp/sample.txt",
                "page_count": 2,
                "block_count": 2,
                "chunk_count": 2,
                "summary": "Претензия по оплате",
                "extracted_facts": {
                    "sender": "ООО Ромашка",
                    "recipient": "ООО Вектор",
                    "claim_subject": "неоплата по акту",
                    "claim_amounts": ["120 000 руб."],
                    "dates": ["01.03.2026"],
                    "referenced_documents": ["договор №15"],
                    "response_deadline": "10 дней",
                    "recipient_position": "заказчик",
                    "legal_risks": [],
                    "missing_information": [],
                },
                "draft_reply": "Проект ответа",
                "warnings": [],
                "raw_response": {
                    "summary": "Претензия по оплате",
                    "extracted_facts": {
                        "sender": "ООО Ромашка",
                        "recipient": "ООО Вектор",
                        "claim_subject": "неоплата по акту",
                        "claim_amounts": ["120 000 руб."],
                        "dates": ["01.03.2026"],
                        "referenced_documents": ["договор №15"],
                        "response_deadline": "10 дней",
                        "recipient_position": "заказчик",
                        "legal_risks": [],
                        "missing_information": [],
                    },
                    "draft_reply": "Проект ответа",
                    "reply_mode_requested": "deny",
                    "reply_mode_effective": "deny",
                    "extraction_status": "text_extracted",
                    "fallback_used": "none",
                },
                "reply_mode_requested": "deny",
                "reply_mode_effective": "deny",
            },
        )()

    monkeypatch.setattr(module, "analyze_pdf_document", fake_analyze)

    rc = module.main(["--file", "sample.pdf", "--task", "claim_response", "--reply-mode", "deny", "--json"])
    out = capsys.readouterr().out

    assert rc == 0
    parsed = json.loads(out)
    assert parsed["summary"] == "Претензия по оплате"
    assert parsed["extracted_facts"]["sender"] == "ООО Ромашка"
    assert parsed["draft_reply"] == "Проект ответа"
    assert parsed["reply_mode_requested"] == "deny"
    assert parsed["reply_mode_effective"] == "deny"


@pytest.mark.asyncio
async def test_neutral_mode_produces_neutral_business_reply(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        return "Уважаемые коллеги, сообщаем результаты рассмотрения претензии."

    monkeypatch.setattr(pdf_pipeline, "chat_raw", fake_chat_raw)

    structured = {
        "summary": "Претензия по оплате.",
        "extracted_facts": {
            "sender": "ООО Ромашка",
            "recipient": "ООО Вектор",
            "claim_subject": "неоплата по акту",
            "claim_amounts": ["120 000 руб."],
            "dates": ["01.03.2026"],
            "referenced_documents": ["договор №15"],
            "response_deadline": "10 дней",
            "recipient_position": "заказчик",
            "legal_risks": [],
            "missing_information": [],
        },
    }

    import httpx

    async with httpx.AsyncClient() as client:
        reply = await generate_claim_reply_from_facts(structured, client=client, reply_mode="neutral")

    assert "результаты рассмотрения" in reply
    assert "reply_mode_effective=neutral" in calls[0][1]


@pytest.mark.asyncio
async def test_deny_mode_avoids_admissions(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        return "Настоящим сообщаем о несогласии с заявленными требованиями."

    monkeypatch.setattr(pdf_pipeline, "chat_raw", fake_chat_raw)

    structured = {
        "summary": "Претензия по оплате.",
        "extracted_facts": {
            "sender": "ООО Ромашка",
            "recipient": "ООО Вектор",
            "claim_subject": "неоплата по акту",
            "claim_amounts": ["120 000 руб."],
            "dates": ["01.03.2026"],
            "referenced_documents": ["договор №15"],
            "response_deadline": "10 дней",
            "recipient_position": "заказчик",
            "legal_risks": [],
            "missing_information": [],
        },
    }

    import httpx

    async with httpx.AsyncClient() as client:
        reply = await generate_claim_reply_from_facts(structured, client=client, reply_mode="deny")

    assert "несогласии" in reply
    assert "reply_mode_effective=deny" in calls[0][1]


@pytest.mark.asyncio
async def test_request_documents_mode_asks_for_supporting_materials(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        return "Просим направить подтверждающие документы и расчёт заявленных требований."

    monkeypatch.setattr(pdf_pipeline, "chat_raw", fake_chat_raw)

    structured = {
        "summary": "Претензия по оплате.",
        "extracted_facts": {
            "sender": "ООО Ромашка",
            "recipient": "ООО Вектор",
            "claim_subject": "неоплата по акту",
            "claim_amounts": ["120 000 руб."],
            "dates": ["01.03.2026"],
            "referenced_documents": ["договор №15"],
            "response_deadline": "10 дней",
            "recipient_position": "заказчик",
            "legal_risks": [],
            "missing_information": [],
        },
    }

    import httpx

    async with httpx.AsyncClient() as client:
        reply = await generate_claim_reply_from_facts(structured, client=client, reply_mode="request_documents")

    assert "подтверждающие документы" in reply
    assert "reply_mode_effective=request_documents" in calls[0][1]


@pytest.mark.asyncio
async def test_settlement_mode_allows_negotiation_without_admitting_liability(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, str]] = []

    async def fake_chat_raw(*, client, system: str, user: str) -> str:
        calls.append((system, user))
        return "Готовы обсудить возможное урегулирование спора в рабочем порядке."

    monkeypatch.setattr(pdf_pipeline, "chat_raw", fake_chat_raw)

    structured = {
        "summary": "Претензия по оплате.",
        "extracted_facts": {
            "sender": "ООО Ромашка",
            "recipient": "ООО Вектор",
            "claim_subject": "неоплата по акту",
            "claim_amounts": ["120 000 руб."],
            "dates": ["01.03.2026"],
            "referenced_documents": ["договор №15"],
            "response_deadline": "10 дней",
            "recipient_position": "заказчик",
            "legal_risks": [],
            "missing_information": [],
        },
    }

    import httpx

    async with httpx.AsyncClient() as client:
        reply = await generate_claim_reply_from_facts(structured, client=client, reply_mode="settlement")

    assert "урегулирование" in reply
    assert "reply_mode_effective=settlement" in calls[0][1]


def test_auto_mode_falls_back_to_conservative_behavior_on_incomplete_facts():
    facts = {
        "sender": "unknown",
        "recipient": "ООО Вектор",
        "claim_subject": "unknown",
        "claim_amounts": [],
        "dates": [],
        "referenced_documents": [],
        "response_deadline": "unknown",
        "recipient_position": "unknown",
        "legal_risks": [],
        "missing_information": [],
    }

    assert resolve_claim_reply_mode(facts, requested_mode="auto") == "request_documents"


def test_cli_validates_reply_mode():
    module = _load_pdf_analyze_module()

    with pytest.raises(SystemExit) as exc:
        module.main(["--file", "sample.pdf", "--reply-mode", "aggressive"])

    assert exc.value.code == 2
