from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from app.schemas.api import FreightTransportOrderFields
from app.services.freight.dogovor_zayavka_text import (
    CLAUSES_MAIN,
    DISPUTES,
    FOOTER_NOTE,
    LIABILITY,
)

_FONT_NAME = "DejaVuSans"


def transport_order_font_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "fonts" / "DejaVuSans.ttf"


def _dash(text: str) -> str:
    t = (text or "").strip()
    return t if t else "—"


def _cargo_description_block(f: FreightTransportOrderFields) -> str:
    parts: list[str] = []
    if f.cargo_name.strip():
        parts.append(f.cargo_name.strip())
    if f.cargo_weight.strip():
        parts.append(f"вес: {f.cargo_weight.strip()}")
    if f.cargo_volume.strip():
        parts.append(f"объём: {f.cargo_volume.strip()}")
    if f.cargo_places.strip():
        parts.append(f"мест: {f.cargo_places.strip()}")
    if f.packaging.strip():
        parts.append(f"упаковка: {f.packaging.strip()}")
    return "; ".join(parts) if parts else "—"


def _route_line(f: FreightTransportOrderFields) -> str:
    if f.route_description.strip():
        return f.route_description.strip()
    a, b = f.loading_address.strip(), f.unloading_address.strip()
    if a and b:
        return f"{a} — {b}"
    return a or b or "—"


def _shipper_line(f: FreightTransportOrderFields) -> str:
    if f.shipper_contact.strip():
        return f.shipper_contact.strip()
    if f.customer_contact.strip():
        return f.customer_contact.strip()
    return "—"


def _delivery_line(f: FreightTransportOrderFields) -> str:
    parts = [f.delivery_deadline.strip(), f.unloading_datetime.strip()]
    parts = [p for p in parts if p]
    return "; ".join(parts) if parts else "—"


def _customer_inn_kpp_lines(f: FreightTransportOrderFields) -> tuple[str, str]:
    inn, kpp = f.customer_inn.strip(), f.customer_kpp.strip()
    if inn or kpp:
        return inn or "—", kpp or "—"
    combined = f.customer_inn_kpp.strip()
    if not combined:
        return "—", "—"
    if "/" in combined:
        a, _, b = combined.partition("/")
        return a.strip() or "—", b.strip() or "—"
    return combined, "—"


def build_transport_order_pdf_bytes(fields: FreightTransportOrderFields) -> bytes:
    font_path = transport_order_font_path()
    if not font_path.is_file():
        raise FileNotFoundError(f"Шрифт для PDF не найден: {font_path}")

    if fields.pdf_template == "simple":
        return _build_simple_pdf(fields, str(font_path))
    return _build_dogovor_zayavka_pdf(fields, str(font_path))


def _build_simple_pdf(fields: FreightTransportOrderFields, font_path: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.add_font(_FONT_NAME, "", font_path)
    col_w = pdf.epw

    pdf.set_font(_FONT_NAME, "", 16)
    title = _dash(fields.document_title) or "Заявка на перевозку груза"
    pdf.multi_cell(col_w, 9, title, align="C")
    pdf.ln(4)

    pdf.set_font(_FONT_NAME, "", 10)
    meta_parts = []
    if fields.order_number.strip():
        meta_parts.append(f"№ {fields.order_number.strip()}")
    if fields.order_date.strip():
        meta_parts.append(f"от {fields.order_date.strip()}")
    if meta_parts:
        pdf.multi_cell(col_w, 6, " ".join(meta_parts), align="C")
        pdf.ln(3)

    def block(heading: str, lines: list[tuple[str, str]]) -> None:
        pdf.set_font(_FONT_NAME, "", 11)
        pdf.multi_cell(col_w, 7, heading)
        pdf.ln(1)
        pdf.set_font(_FONT_NAME, "", 10)
        for label, val in lines:
            if not (label or "").strip():
                continue
            pdf.multi_cell(col_w, 5, f"{label}: {_dash(val)}")
        pdf.ln(2)

    block(
        "Заказчик",
        [
            ("Наименование", fields.customer_name),
            ("ИНН / КПП", fields.customer_inn_kpp),
            ("Адрес", fields.customer_address),
            ("Телефон", fields.customer_phone),
            ("Контактное лицо", fields.customer_contact),
        ],
    )
    block(
        "Перевозчик (если известен)",
        [
            ("Наименование", fields.carrier_name),
            ("Реквизиты / примечание", fields.carrier_details),
        ],
    )
    block(
        "Погрузка",
        [
            ("Адрес / объект", fields.loading_address),
            ("Дата и время", fields.loading_datetime),
        ],
    )
    block(
        "Выгрузка",
        [
            ("Адрес / объект", fields.unloading_address),
            ("Дата и время", fields.unloading_datetime),
        ],
    )
    block(
        "Груз и условия",
        [
            ("Наименование / описание", fields.cargo_name),
            ("Масса", fields.cargo_weight),
            ("Объём", fields.cargo_volume),
            ("Количество мест", fields.cargo_places),
            ("Упаковка", fields.packaging),
            ("Требования к ТС", fields.vehicle_requirements),
            ("Условия оплаты / ставка", fields.price_terms),
        ],
    )
    if fields.additional_terms.strip():
        block("Дополнительные условия", [("", fields.additional_terms)])

    pdf.ln(4)
    pdf.set_font(_FONT_NAME, "", 9)
    pdf.multi_cell(
        col_w,
        5,
        "Документ сформирован автоматически как черновик. Подпись, печать и юридическая "
        "проверка — перед отправкой контрагенту.",
    )

    return _pdf_output_bytes(pdf)


def _paragraph(pdf: FPDF, w: float, text: str, *, size: int = 9, lh: float = 4.5) -> None:
    pdf.set_font(_FONT_NAME, "", size)
    pdf.multi_cell(w, lh, text)
    pdf.ln(1)


def _labeled_row(pdf: FPDF, w: float, label: str, value: str, *, lh: float = 4.2) -> None:
    pdf.set_font(_FONT_NAME, "", 8)
    pdf.multi_cell(w, lh, label)
    pdf.set_font(_FONT_NAME, "", 9)
    pdf.multi_cell(w, lh + 0.3, _dash(value))
    pdf.ln(0.5)


def _requisites_column(
    pdf: FPDF,
    x: float,
    col_w: float,
    title: str,
    org: str,
    address: str,
    inn: str,
    kpp: str,
    ogrn: str,
    rs: str,
    bank: str,
    bik: str,
    ks: str,
    city: str,
    extra_lines: list[tuple[str, str]],
) -> float:
    pdf.set_x(x)
    pdf.set_font(_FONT_NAME, "", 9)
    pdf.multi_cell(col_w, 5, title)
    pdf.set_x(x)
    pdf.set_font(_FONT_NAME, "", 8)
    pdf.multi_cell(col_w, 4, f"Наименование: {_dash(org)}")
    pdf.set_x(x)
    pdf.multi_cell(col_w, 4, f"Юридический адрес: {_dash(address)}")
    pdf.set_x(x)
    pdf.multi_cell(col_w, 4, f"ИНН: {inn}  КПП: {kpp}")
    pdf.set_x(x)
    pdf.multi_cell(col_w, 4, f"ОГРН: {_dash(ogrn)}")
    pdf.set_x(x)
    pdf.multi_cell(col_w, 4, f"Р/с: {_dash(rs)}")
    pdf.set_x(x)
    pdf.multi_cell(col_w, 4, f"Банк: {_dash(bank)}")
    pdf.set_x(x)
    pdf.multi_cell(col_w, 4, f"БИК: {_dash(bik)}  Город: {_dash(city)}")
    pdf.set_x(x)
    pdf.multi_cell(col_w, 4, f"К/с: {_dash(ks)}")
    for lab, val in extra_lines:
        if not val.strip():
            continue
        pdf.set_x(x)
        pdf.multi_cell(col_w, 4, f"{lab}: {val.strip()}")
    return pdf.get_y()


def _build_dogovor_zayavka_pdf(fields: FreightTransportOrderFields, font_path: str) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.add_font(_FONT_NAME, "", font_path)
    w = pdf.epw

    no = fields.order_number.strip() or "_______"
    dt = fields.order_date.strip() or "«___» __________ ____ г."
    title = (
        f"Договор-заявка № {no} от {dt} на разовую перевозку груза на автомобильном транспорте"
    )
    pdf.set_font(_FONT_NAME, "", 11)
    pdf.multi_cell(w, 5.5, title, align="C")
    pdf.ln(3)

    org = fields.customer_name.strip() or "_______________________________"
    if fields.customer_representative_position.strip() and fields.customer_representative_name.strip():
        vlice = (
            f"в лице {fields.customer_representative_position.strip()} "
            f"{fields.customer_representative_name.strip()}"
        )
    else:
        vlice = "в лице ________________________________________________"

    if fields.carrier_name.strip():
        carrier_line = f"{fields.carrier_name.strip()}, именуемый(ая) в дальнейшем «Перевозчик»"
    else:
        carrier_line = "_______________________________, именуемый(ая) в дальнейшем «Перевозчик»"

    preamble = (
        f"{org}, именуемое в дальнейшем «Заказчик», {vlice} с одной стороны и {carrier_line}, "
        f"с другой стороны, подписали настоящий заказ на выполнение перевозки груза на следующих условиях:"
    )
    _paragraph(pdf, w, preamble, size=9, lh=5)

    pdf.ln(1)
    pdf.set_font(_FONT_NAME, "", 10)
    pdf.multi_cell(w, 5, "Условия выполнения договора-заявки")
    pdf.ln(1)

    rows: list[tuple[str, str]] = [
        ("Маршрут", _route_line(fields)),
        ("Описание груза, вес/объём, характер упаковки", _cargo_description_block(fields)),
        ("Способ погрузки/разгрузки", fields.loading_unloading_method),
        ("Адрес погрузки", fields.loading_address),
        ("Дата, время погрузки", fields.loading_datetime),
        ("Грузоотправитель, телефон контакта", _shipper_line(fields)),
        ("Адрес разгрузки", fields.unloading_address),
        ("Грузополучатель, телефон контакта", fields.consignee_contact),
        ("Требования к автотранспорту", fields.vehicle_requirements),
        ("Срок доставки, время разгрузки", _delivery_line(fields)),
        ("Выделяемый автомобиль, госномер", fields.vehicle_plate),
        ("Паспортные данные водителя, тел. контакта", fields.driver_passport_phone),
        ("Стоимость перевозки, способ оплаты", fields.price_terms),
        ("Срок оплаты", fields.payment_deadline),
        ("Примечания и дополнительные условия", fields.additional_terms),
    ]
    for label, val in rows:
        _labeled_row(pdf, w, label, val)

    pdf.ln(2)
    _paragraph(pdf, w, CLAUSES_MAIN, size=8, lh=4.2)
    _paragraph(pdf, w, DISPUTES, size=8, lh=4.2)
    _paragraph(pdf, w, LIABILITY, size=8, lh=4.2)

    pdf.ln(3)
    pdf.set_font(_FONT_NAME, "", 10)
    pdf.multi_cell(w, 5, "Реквизиты и подписи сторон:")
    pdf.ln(2)

    inn_c, kpp_c = _customer_inn_kpp_lines(fields)
    cust_extra: list[tuple[str, str]] = []
    if fields.customer_phone.strip():
        cust_extra.append(("Тел.", fields.customer_phone))
    if fields.ati_code.strip():
        cust_extra.append(("КОД АТИ", fields.ati_code))
    if fields.logist_name.strip():
        cust_extra.append(("Логист", fields.logist_name))

    car_extra: list[tuple[str, str]] = []
    if fields.carrier_details.strip():
        car_extra.append(("Примечание", fields.carrier_details))

    gap = 3.0
    col_w = (w - gap) / 2
    x_l = pdf.l_margin
    x_r = x_l + col_w + gap
    y0 = pdf.get_y()

    pdf.set_xy(x_l, y0)
    y_after_l = _requisites_column(
        pdf,
        x_l,
        col_w,
        "Заказчик:",
        fields.customer_name,
        fields.customer_address,
        inn_c,
        kpp_c,
        fields.customer_ogrn,
        fields.customer_rs,
        fields.customer_bank,
        fields.customer_bik,
        fields.customer_ks,
        fields.customer_legal_city,
        cust_extra,
    )

    carrier_addr = fields.carrier_legal_address.strip() or fields.carrier_details.strip()
    pdf.set_xy(x_r, y0)
    y_after_r = _requisites_column(
        pdf,
        x_r,
        col_w,
        "Перевозчик:",
        fields.carrier_name,
        carrier_addr,
        fields.carrier_inn,
        fields.carrier_kpp,
        fields.carrier_ogrn,
        fields.carrier_rs,
        fields.carrier_bank,
        fields.carrier_bik,
        fields.carrier_ks,
        "",
        car_extra,
    )

    pdf.set_y(max(y_after_l, y_after_r) + 8)
    pdf.set_font(_FONT_NAME, "", 9)
    pdf.multi_cell(w, 5, "_________________ /_________________/  подпись                        М.П.")
    pdf.ln(5)
    pdf.multi_cell(w, 5, "_________________/__________________/  подпись                              М.П.")

    pdf.ln(6)
    pdf.set_font(_FONT_NAME, "", 7)
    pdf.multi_cell(w, 3.5, FOOTER_NOTE)

    return _pdf_output_bytes(pdf)


def _pdf_output_bytes(pdf: FPDF) -> bytes:
    out = pdf.output()
    if isinstance(out, str):
        return out.encode("latin-1")
    if isinstance(out, bytearray):
        return bytes(out)
    return bytes(out)
