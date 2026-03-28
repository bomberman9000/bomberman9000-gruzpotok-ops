from unittest.mock import AsyncMock, patch

from app.core.config import get_settings


def test_transport_order_pdf_proxy_returns_pdf_bytes(monkeypatch):
    monkeypatch.setenv("RAG_API_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()

    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj trailer<<>>\n%%EOF\n"
    with patch(
        "app.api.ai_routes.RagApiClient.transport_order_pdf",
        new_callable=AsyncMock,
        return_value=(pdf, "rid-pdf-test", 3),
    ):
        from fastapi.testclient import TestClient

        from app.main import app

        c = TestClient(app)
        r = c.post(
            "/api/v1/ai/freight/transport-order-pdf",
            json={
                "pdf_engine": "fpdf",
                "customer_name": "ООО Тест",
                "loading_address": "Москва, склад 1",
                "unloading_address": "Казань, терминал 2",
                "cargo_name": "Оборудование 10 т",
            },
        )
    assert r.status_code == 200
    assert r.headers.get("content-type") == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert "attachment" in (r.headers.get("content-disposition") or "").lower()
    assert r.headers.get("X-Request-ID") == "rid-pdf-test"


def test_transport_order_pdf_proxy_503_when_rag_disabled(monkeypatch):
    monkeypatch.setenv("RAG_API_ENABLED", "false")
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()

    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).post(
        "/api/v1/ai/freight/transport-order-pdf",
        json={
            "customer_name": "ООО Тест",
            "loading_address": "Москва, склад 1",
            "unloading_address": "Казань, терминал 2",
            "cargo_name": "Оборудование 10 т",
        },
    )
    assert r.status_code == 503
