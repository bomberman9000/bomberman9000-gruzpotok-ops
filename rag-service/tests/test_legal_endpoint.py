import pytest
from fpdf import FPDF
from PIL import Image, ImageDraw
from pathlib import Path
import shutil
import uuid

from app.schemas.api import LegalClaimComposeRequest, LegalClaimReviewRequest
from app.services.business.rules import MIN_CLAIM_TEXT_LEN, validate_claim_compose_input, validate_claim_review_input
from app.services.gruzpotok_flow import legal_claim_compose, legal_claim_review


@pytest.fixture
def work_dir() -> Path:
    root = Path(__file__).resolve().parents[2] / "_pytest_legal_endpoint"
    root.mkdir(exist_ok=True)
    path = root / uuid.uuid4().hex
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.mark.asyncio
async def test_claim_review_short_text_no_llm():
    body = LegalClaimReviewRequest(claim_text="x" * (MIN_CLAIM_TEXT_LEN - 1))
    import httpx

    async with httpx.AsyncClient() as client:
        out = await legal_claim_review(client, body)
    assert out.llm_invoked is False
    assert out.missing_information
    assert out.persona == "legal"


@pytest.mark.asyncio
async def test_claim_review_requires_minimum_length_message():
    miss = validate_claim_review_input("short")
    assert miss and "коротк" in miss[0].lower()


@pytest.mark.asyncio
async def test_claim_compose_short_facts_no_llm():
    body = LegalClaimComposeRequest(facts="x" * (MIN_CLAIM_TEXT_LEN - 1))
    import httpx

    async with httpx.AsyncClient() as client:
        out = await legal_claim_compose(client, body)
    assert out.llm_invoked is False
    assert out.missing_facts
    assert out.persona == "legal"


def test_claim_compose_requires_minimum_length_message():
    miss = validate_claim_compose_input("short")
    assert miss and "коротк" in miss[0].lower()


def _font_path() -> Path:
    return Path(__file__).resolve().parents[1] / "app" / "assets" / "fonts" / "DejaVuSans.ttf"


def _write_pdf(path: Path, text: str) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_font("DejaVuSans", "", str(_font_path()))
    pdf.add_page()
    pdf.set_font("DejaVuSans", "", 12)
    pdf.multi_cell(0, 8, text)
    raw = pdf.output()
    path.write_bytes(raw.encode("latin-1") if isinstance(raw, str) else bytes(raw))


def _write_scan_only_pdf(path: Path, text: str) -> None:
    img = Image.new("RGB", (1200, 1600), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((80, 120), text, fill="black")
    img.save(path, "PDF")


@pytest.mark.asyncio
async def test_claim_review_uses_document_extraction_when_claim_text_is_pdf_path(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(work_dir))
    pdf_path = work_dir / "pretension.pdf"
    _write_pdf(
        pdf_path,
        "Претензия по договору поставки. Отправитель: ООО Ромашка. Сумма требований: 120 000 руб.",
    )

    captured_query: dict[str, str] = {}

    class DummyResult:
        answer = '{"summary":"ok","legal_risks":[],"missing_information":[],"recommended_position":"позиция"}'
        citations = []
        llm_invoked = True
        insufficient_data = False
        mode = "strict"
        retrieval_debug = None

    async def fake_execute_rag_query(client, **kwargs):
        captured_query["query"] = kwargs["query"]
        return DummyResult()

    monkeypatch.setattr("app.services.gruzpotok_flow.execute_rag_query", fake_execute_rag_query)

    body = LegalClaimReviewRequest(claim_text=str(pdf_path))
    import httpx

    async with httpx.AsyncClient() as client:
        out = await legal_claim_review(client, body)

    assert out.llm_invoked is True
    assert "ООО Ромашка" in captured_query["query"]
    assert "120 000 руб." in captured_query["query"]
    assert str(pdf_path) not in captured_query["query"]


@pytest.mark.asyncio
async def test_claim_review_returns_clear_tech_reason_for_missing_pdf(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(work_dir))
    missing = work_dir / "missing.pdf"
    body = LegalClaimReviewRequest(claim_text=str(missing))
    import httpx

    async with httpx.AsyncClient() as client:
        out = await legal_claim_review(client, body)

    assert out.llm_invoked is False
    assert "Не удалось извлечь текст документа" in out.summary
    assert "document_input_error=file_not_found" in out.missing_information


@pytest.mark.asyncio
async def test_claim_review_scan_only_pdf_is_not_reported_as_empty(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(work_dir))
    pdf_path = work_dir / "scan.pdf"
    _write_scan_only_pdf(pdf_path, "Претензия на 120 000 руб.")
    body = LegalClaimReviewRequest(claim_text=str(pdf_path))
    import httpx

    async with httpx.AsyncClient() as client:
        out = await legal_claim_review(client, body)

    assert out.llm_invoked is False
    assert "текстовый слой" in out.summary.lower()
    assert "скан" in out.summary.lower()
    assert "пуст" not in out.summary.lower()
    assert "document_input_error=no_text_layer_but_pages_present" in out.missing_information


@pytest.mark.asyncio
async def test_claim_compose_uses_document_extraction_when_facts_is_pdf_path(work_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(work_dir))
    pdf_path = work_dir / "facts.pdf"
    _write_pdf(
        pdf_path,
        "Исходящая претензия. Поставщик нарушил срок оплаты. Сумма задолженности 85 000 руб.",
    )

    captured_query: dict[str, str] = {}

    class DummyResult:
        answer = '{"draft_claim_text":"черновик","missing_facts":[],"disclaimers":["ok"]}'
        citations = []
        llm_invoked = True
        insufficient_data = False
        mode = "draft"
        retrieval_debug = None

    async def fake_execute_rag_query(client, **kwargs):
        captured_query["query"] = kwargs["query"]
        return DummyResult()

    monkeypatch.setattr("app.services.gruzpotok_flow.execute_rag_query", fake_execute_rag_query)

    body = LegalClaimComposeRequest(facts=str(pdf_path))
    import httpx

    async with httpx.AsyncClient() as client:
        out = await legal_claim_compose(client, body)

    assert out.llm_invoked is True
    assert "85 000 руб." in captured_query["query"]
    assert "нарушил срок оплаты" in captured_query["query"]
    assert str(pdf_path) not in captured_query["query"]


@pytest.mark.asyncio
async def test_claim_compose_plain_text_still_works_as_plain_text(monkeypatch: pytest.MonkeyPatch):
    captured_query: dict[str, str] = {}

    class DummyResult:
        answer = '{"draft_claim_text":"черновик","missing_facts":[],"disclaimers":["ok"]}'
        citations = []
        llm_invoked = True
        insufficient_data = False
        mode = "draft"
        retrieval_debug = None

    async def fake_execute_rag_query(client, **kwargs):
        captured_query["query"] = kwargs["query"]
        return DummyResult()

    monkeypatch.setattr("app.services.gruzpotok_flow.execute_rag_query", fake_execute_rag_query)

    facts = "Контрагент просрочил оплату по договору поставки, сумма 42 000 руб., просим оплатить задолженность."
    body = LegalClaimComposeRequest(facts=facts)
    import httpx

    async with httpx.AsyncClient() as client:
        out = await legal_claim_compose(client, body)

    assert out.llm_invoked is True
    assert facts in captured_query["query"]
