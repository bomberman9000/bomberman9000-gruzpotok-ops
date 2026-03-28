import pytest
from pydantic import ValidationError

from app.schemas.api import FreightTransportOrderPdfRequest
from app.services.business.rules import validate_transport_order_compose_input
from app.services.freight.libreoffice_pdf import LibreOfficePdfError, build_transport_order_pdf_via_libreoffice
from app.services.freight.transport_order_pdf import build_transport_order_pdf_bytes
from app.services.gruzpotok_flow import freight_transport_order_compose


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
