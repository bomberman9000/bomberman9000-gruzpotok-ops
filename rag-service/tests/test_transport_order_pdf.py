import logging

import pytest
from pydantic import ValidationError
from pathlib import Path
import shutil
import uuid

from app.schemas.api import FreightTransportOrderPdfRequest
from app.services.business.rules import validate_transport_order_compose_input
from app.services.freight.libreoffice_pdf import LibreOfficePdfError, build_transport_order_pdf_via_libreoffice
from app.services.freight.transport_order_pdf import build_transport_order_pdf_bytes
from app.services.gruzpotok_flow import freight_transport_order_compose


@pytest.fixture
def work_dir() -> Path:
    root = Path(__file__).resolve().parents[2] / "_pytest_transport_order"
    root.mkdir(exist_ok=True)
    path = root / uuid.uuid4().hex
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_transport_order_pdf_starts_with_pdf_magic():
    body = FreightTransportOrderPdfRequest(
        customer_name="OOO Test",
        loading_address="Moscow, warehouse 1",
        unloading_address="Saint Petersburg",
        cargo_name="Pallets, 10 places",
    )
    raw = build_transport_order_pdf_bytes(body)
    assert raw[:4] == b"%PDF"


def test_transport_order_pdf_cyrillic_ok():
    body = FreightTransportOrderPdfRequest(
        customer_name="\u041e\u041e\u041e \u0422\u0435\u0441\u0442",
        loading_address="\u041c\u043e\u0441\u043a\u0432\u0430",
        unloading_address="\u0422\u0432\u0435\u0440\u044c",
        cargo_name="\u041f\u0430\u043b\u043b\u0435\u0442\u044b",
    )
    raw = build_transport_order_pdf_bytes(body)
    assert raw[:4] == b"%PDF"


def test_transport_order_pdf_simple_template():
    body = FreightTransportOrderPdfRequest(
        pdf_template="simple",
        customer_name="OOO X",
        loading_address="A",
        unloading_address="B",
        cargo_name="boxes",
    )
    raw = build_transport_order_pdf_bytes(body)
    assert raw[:4] == b"%PDF"


def test_libreoffice_engine_rejects_simple_template():
    body = FreightTransportOrderPdfRequest(
        pdf_engine="libreoffice",
        pdf_template="simple",
        customer_name="OOO X",
        loading_address="Moscow",
        unloading_address="SPb",
        cargo_name="x",
    )
    with pytest.raises(LibreOfficePdfError, match="dogovor_zayavka"):
        build_transport_order_pdf_via_libreoffice(body, soffice_executable=None)


def test_transport_order_pdf_validation_too_sparse():
    with pytest.raises(ValidationError):
        FreightTransportOrderPdfRequest(customer_name="ab")


def test_validate_transport_order_compose_short():
    miss = validate_transport_order_compose_input("коротко")
    assert miss


@pytest.mark.asyncio
async def test_transport_order_compose_short_no_llm():
    import httpx

    from app.schemas.api import FreightTransportOrderComposeRequest

    body = FreightTransportOrderComposeRequest(request_text="x" * 10)
    async with httpx.AsyncClient() as client:
        out = await freight_transport_order_compose(client, body)
    assert out.llm_invoked is False
    assert out.missing_information


@pytest.mark.asyncio
async def test_transport_order_compose_uses_document_extraction_when_request_text_is_txt_path(
    work_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(work_dir))
    txt_path = work_dir / "request.txt"
    txt_path.write_text(
        "Заявка на перевозку: груз паллеты, погрузка Самара, выгрузка Москва, стоимость 95 000 руб.",
        encoding="utf-8",
    )

    captured_query: dict[str, str] = {}

    class DummyResult:
        answer = '{"customer_name":"","loading_address":"Самара","unloading_address":"Москва","cargo_name":"паллеты","missing_information":[]}'
        citations = []
        llm_invoked = True
        insufficient_data = False
        mode = "draft"
        retrieval_debug = None

    async def fake_execute_rag_query(client, **kwargs):
        captured_query["query"] = kwargs["query"]
        return DummyResult()

    monkeypatch.setattr("app.services.gruzpotok_flow.execute_rag_query", fake_execute_rag_query)
    caplog.set_level(logging.INFO, logger="app.services.gruzpotok_flow")

    from app.schemas.api import FreightTransportOrderComposeRequest

    body = FreightTransportOrderComposeRequest(request_text=str(txt_path))
    import httpx

    async with httpx.AsyncClient() as client:
        out = await freight_transport_order_compose(client, body)

    assert out.llm_invoked is True
    assert "погрузка Самара" in captured_query["query"]
    assert "выгрузка Москва" in captured_query["query"]
    assert str(txt_path) not in captured_query["query"]
    assert "mode=document_pipeline" in caplog.text


@pytest.mark.asyncio
async def test_transport_order_compose_returns_clear_tech_reason_for_missing_txt(
    work_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.schemas.api import FreightTransportOrderComposeRequest
    import httpx

    monkeypatch.setenv("RAG_DOCUMENT_INPUT_ROOT", str(work_dir))
    missing = work_dir / "missing.txt"
    body = FreightTransportOrderComposeRequest(request_text=str(missing))

    async with httpx.AsyncClient() as client:
        out = await freight_transport_order_compose(client, body)

    assert out.llm_invoked is False
    assert "document_input_error=file_not_found" in out.missing_information


@pytest.mark.asyncio
async def test_transport_order_compose_unsupported_suffix_remains_plain_text(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    captured_query: dict[str, str] = {}

    class DummyResult:
        answer = '{"customer_name":"","loading_address":"","unloading_address":"","cargo_name":"","missing_information":[]}'
        citations = []
        llm_invoked = True
        insufficient_data = False
        mode = "draft"
        retrieval_debug = None

    async def fake_execute_rag_query(client, **kwargs):
        captured_query["query"] = kwargs["query"]
        return DummyResult()

    monkeypatch.setattr("app.services.gruzpotok_flow.execute_rag_query", fake_execute_rag_query)
    caplog.set_level(logging.INFO, logger="app.services.gruzpotok_flow")

    from app.schemas.api import FreightTransportOrderComposeRequest
    import httpx

    request_text = r"C:\docs\request.bin"
    body = FreightTransportOrderComposeRequest(
        request_text=f"Смотри исходник {request_text}, груз 10 паллет, маршрут Самара-Москва."
    )

    async with httpx.AsyncClient() as client:
        out = await freight_transport_order_compose(client, body)

    assert out.llm_invoked is True
    assert request_text in captured_query["query"]
    assert "mode=plain_text" in caplog.text
