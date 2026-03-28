"""Тела запросов к rag-api для заявки на перевозку (синхронно со схемой rag-service)."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class AITransportOrderComposeBody(BaseModel):
    request_text: str = Field(..., min_length=1, max_length=16000)
    debug: bool = False


class AITransportOrderPdfBody(BaseModel):
    pdf_engine: Literal["fpdf", "libreoffice"] = Field(default="fpdf")
    pdf_template: Literal["simple", "dogovor_zayavka"] = Field(default="dogovor_zayavka")
    document_title: str = Field(default="Заявка на перевозку груза", max_length=500)
    order_number: str = Field(default="", max_length=200)
    order_date: str = Field(default="", max_length=200)
    customer_name: str = Field(default="", max_length=1000)
    customer_representative_position: str = Field(default="", max_length=500)
    customer_representative_name: str = Field(default="", max_length=500)
    customer_inn_kpp: str = Field(default="", max_length=200)
    customer_inn: str = Field(default="", max_length=20)
    customer_kpp: str = Field(default="", max_length=20)
    customer_ogrn: str = Field(default="", max_length=20)
    customer_rs: str = Field(default="", max_length=50)
    customer_bank: str = Field(default="", max_length=500)
    customer_bik: str = Field(default="", max_length=20)
    customer_ks: str = Field(default="", max_length=50)
    customer_legal_city: str = Field(default="", max_length=200)
    customer_address: str = Field(default="", max_length=2000)
    customer_phone: str = Field(default="", max_length=200)
    customer_contact: str = Field(default="", max_length=500)
    carrier_name: str = Field(default="", max_length=1000)
    carrier_details: str = Field(default="", max_length=2000)
    carrier_legal_address: str = Field(default="", max_length=2000)
    carrier_inn: str = Field(default="", max_length=20)
    carrier_kpp: str = Field(default="", max_length=20)
    carrier_ogrn: str = Field(default="", max_length=20)
    carrier_rs: str = Field(default="", max_length=50)
    carrier_bank: str = Field(default="", max_length=500)
    carrier_bik: str = Field(default="", max_length=20)
    carrier_ks: str = Field(default="", max_length=50)
    route_description: str = Field(default="", max_length=2000)
    loading_unloading_method: str = Field(default="", max_length=500)
    shipper_contact: str = Field(default="", max_length=1000)
    consignee_contact: str = Field(default="", max_length=1000)
    loading_address: str = Field(default="", max_length=2000)
    loading_datetime: str = Field(default="", max_length=500)
    unloading_address: str = Field(default="", max_length=2000)
    unloading_datetime: str = Field(default="", max_length=500)
    delivery_deadline: str = Field(default="", max_length=500)
    cargo_name: str = Field(default="", max_length=4000)
    cargo_weight: str = Field(default="", max_length=200)
    cargo_volume: str = Field(default="", max_length=200)
    cargo_places: str = Field(default="", max_length=200)
    packaging: str = Field(default="", max_length=1000)
    vehicle_requirements: str = Field(default="", max_length=2000)
    vehicle_plate: str = Field(default="", max_length=100)
    driver_passport_phone: str = Field(default="", max_length=500)
    price_terms: str = Field(default="", max_length=2000)
    payment_deadline: str = Field(default="", max_length=500)
    ati_code: str = Field(default="", max_length=50)
    logist_name: str = Field(default="", max_length=300)
    additional_terms: str = Field(default="", max_length=8000)

    @model_validator(mode="after")
    def _min_content_for_pdf(self) -> Self:
        blob = " ".join(
            [
                self.customer_name,
                self.loading_address,
                self.unloading_address,
                self.cargo_name,
                self.customer_address,
                self.route_description,
            ]
        ).strip()
        if len(blob) < 10:
            raise ValueError(
                "Недостаточно данных для PDF: укажите заказчика, маршрут и/или описание груза."
            )
        return self
