from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from html import escape
from pathlib import Path

from app.schemas.api import FreightTransportOrderFields
from app.services.freight.dogovor_zayavka_text import (
    CLAUSES_MAIN,
    DISPUTES,
    FOOTER_NOTE,
    LIABILITY,
)
from app.services.freight.transport_order_pdf import (
    _cargo_description_block,
    _customer_inn_kpp_lines,
    _dash,
    _delivery_line,
    _route_line,
    _shipper_line,
)

logger = logging.getLogger(__name__)


class LibreOfficePdfError(Exception):
    """Не удалось получить PDF через LibreOffice (нет soffice, таймаут, ошибка конвертации)."""


def resolve_soffice_executable(explicit: str | None) -> Path:
    if explicit and explicit.strip():
        p = Path(explicit.strip())
        if p.is_file():
            return p
        raise LibreOfficePdfError(f"LIBREOFFICE_SOFFICE_PATH указывает на несуществующий файл: {p}")

    env_p = (os.environ.get("LIBREOFFICE_SOFFICE_PATH") or "").strip()
    if env_p:
        p = Path(env_p)
        if p.is_file():
            return p
        raise LibreOfficePdfError(f"LIBREOFFICE_SOFFICE_PATH в окружении неверен: {p}")

    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return Path(found)

    win_candidates = [
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    ]
    for p in win_candidates:
        if p.is_file():
            return p

    raise LibreOfficePdfError(
        "LibreOffice не найден: задайте LIBREOFFICE_SOFFICE_PATH (полный путь к soffice.exe / soffice) "
        "или установите LibreOffice и добавьте soffice в PATH."
    )


def _h(s: str) -> str:
    return escape(s or "", quote=False)


def build_dogovor_zayavka_html(fields: FreightTransportOrderFields) -> str:
    no = fields.order_number.strip() or "_______"
    dt = fields.order_date.strip() or "«___» __________ ____ г."
    title = (
        f"Договор-заявка № {no} от {dt} на разовую перевозку груза на автомобильном транспорте"
    )

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

    inn_c, kpp_c = _customer_inn_kpp_lines(fields)
    carrier_addr = fields.carrier_legal_address.strip() or fields.carrier_details.strip()

    rows = [
        ("Маршрут", _route_line(fields)),
        ("Описание груза, вес/объём, характер упаковки", _cargo_description_block(fields)),
        ("Способ погрузки/разгрузки", _dash(fields.loading_unloading_method)),
        ("Адрес погрузки", _dash(fields.loading_address)),
        ("Дата, время погрузки", _dash(fields.loading_datetime)),
        ("Грузоотправитель, телефон контакта", _shipper_line(fields)),
        ("Адрес разгрузки", _dash(fields.unloading_address)),
        ("Грузополучатель, телефон контакта", _dash(fields.consignee_contact)),
        ("Требования к автотранспорту", _dash(fields.vehicle_requirements)),
        ("Срок доставки, время разгрузки", _delivery_line(fields)),
        ("Выделяемый автомобиль, госномер", _dash(fields.vehicle_plate)),
        ("Паспортные данные водителя, тел. контакта", _dash(fields.driver_passport_phone)),
        ("Стоимость перевозки, способ оплаты", _dash(fields.price_terms)),
        ("Срок оплаты", _dash(fields.payment_deadline)),
        ("Примечания и дополнительные условия", _dash(fields.additional_terms)),
    ]

    tr_html = "".join(
        f"<tr><td class='lbl'>{_h(l)}</td><td>{_h(v)}</td></tr>" for l, v in rows
    )

    cust_extra = []
    if fields.customer_phone.strip():
        cust_extra.append(f"Тел.: {_h(fields.customer_phone)}")
    if fields.ati_code.strip():
        cust_extra.append(f"КОД АТИ: {_h(fields.ati_code)}")
    if fields.logist_name.strip():
        cust_extra.append(f"Логист: {_h(fields.logist_name)}")
    cust_extra_html = "<br/>".join(cust_extra) if cust_extra else ""

    car_extra = ""
    if fields.carrier_details.strip() and fields.carrier_details.strip() != carrier_addr:
        car_extra = f"<br/>Примечание: {_h(fields.carrier_details)}"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
body {{ font-family: "Liberation Sans", Arial, sans-serif; font-size: 10pt; margin: 12mm; }}
h1 {{ text-align: center; font-size: 12pt; font-weight: bold; margin-bottom: 1em; }}
.preamble {{ text-align: justify; margin-bottom: 1em; }}
h2 {{ font-size: 11pt; margin-top: 0.8em; }}
table.cond {{ width: 100%; border-collapse: collapse; margin-bottom: 1em; }}
table.cond td {{ border: 1px solid #333; padding: 4px; vertical-align: top; }}
table.cond td.lbl {{ width: 38%; font-size: 8pt; }}
.clauses {{ font-size: 8pt; text-align: justify; white-space: pre-wrap; margin-bottom: 0.8em; }}
.cols {{ display: table; width: 100%; margin-top: 1em; }}
.col {{ display: table-cell; width: 50%; vertical-align: top; padding-right: 8px; font-size: 9pt; }}
.sig {{ margin-top: 2em; font-size: 10pt; }}
.footer {{ font-size: 7pt; color: #444; margin-top: 1.5em; }}
</style></head><body>
<h1>{_h(title)}</h1>
<p class="preamble">{_h(preamble)}</p>
<h2>Условия выполнения договора-заявки</h2>
<table class="cond">{tr_html}</table>
<div class="clauses">{_h(CLAUSES_MAIN)}</div>
<div class="clauses">{_h(DISPUTES)}</div>
<div class="clauses">{_h(LIABILITY)}</div>
<h2>Реквизиты и подписи сторон</h2>
<div class="cols">
<div class="col"><strong>Заказчик:</strong><br/>
Наименование: {_h(fields.customer_name)}<br/>
Юридический адрес: {_h(fields.customer_address)}<br/>
ИНН: {_h(inn_c)} КПП: {_h(kpp_c)}<br/>
ОГРН: {_h(fields.customer_ogrn)}<br/>
Р/с: {_h(fields.customer_rs)}<br/>
Банк: {_h(fields.customer_bank)}<br/>
БИК: {_h(fields.customer_bik)} Город: {_h(fields.customer_legal_city)}<br/>
К/с: {_h(fields.customer_ks)}<br/>
{cust_extra_html}
</div>
<div class="col"><strong>Перевозчик:</strong><br/>
Наименование: {_h(fields.carrier_name)}<br/>
Юридический адрес: {_h(carrier_addr)}<br/>
ИНН: {_h(fields.carrier_inn)} КПП: {_h(fields.carrier_kpp)}<br/>
ОГРН: {_h(fields.carrier_ogrn)}<br/>
Р/с: {_h(fields.carrier_rs)}<br/>
Банк: {_h(fields.carrier_bank)}<br/>
БИК: {_h(fields.carrier_bik)}<br/>
К/с: {_h(fields.carrier_ks)}<br/>
{car_extra}
</div>
</div>
<div class="sig">_________________ /_________________/ подпись &nbsp;&nbsp;&nbsp; М.П.<br/><br/>
_________________/__________________/ подпись &nbsp;&nbsp;&nbsp; М.П.</div>
<p class="footer">{_h(FOOTER_NOTE)}</p>
</body></html>"""


def convert_html_to_pdf_with_libreoffice(
    html: str,
    *,
    soffice_path: Path,
    timeout_sec: float = 90.0,
) -> bytes:
    with tempfile.TemporaryDirectory(prefix="rag_lo_") as tmp:
        tdir = Path(tmp)
        html_path = tdir / "document.html"
        html_path.write_text(html, encoding="utf-8")
        cmd = [
            str(soffice_path),
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tdir),
            str(html_path),
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as e:
            raise LibreOfficePdfError(f"LibreOffice: таймаут {timeout_sec} с") from e
        except OSError as e:
            raise LibreOfficePdfError(f"LibreOffice: не удалось запустить {soffice_path}: {e}") from e

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()[:2000]
            logger.warning("soffice failed rc=%s err=%s", proc.returncode, err)
            raise LibreOfficePdfError(f"LibreOffice завершился с кодом {proc.returncode}: {err or 'нет текста ошибки'}")

        pdf_path = tdir / "document.pdf"
        if not pdf_path.is_file():
            raise LibreOfficePdfError(f"После конвертации не найден {pdf_path}")

        return pdf_path.read_bytes()


def build_transport_order_pdf_via_libreoffice(
    fields: FreightTransportOrderFields,
    *,
    soffice_executable: str | None = None,
) -> bytes:
    if fields.pdf_template == "simple":
        raise LibreOfficePdfError(
            "Режим pdf_engine=libreoffice поддерживается только для pdf_template=dogovor_zayavka; "
            "для simple используйте fpdf."
        )
    soffice = resolve_soffice_executable(soffice_executable)
    html = build_dogovor_zayavka_html(fields)
    return convert_html_to_pdf_with_libreoffice(
        html, soffice_path=soffice, timeout_sec=timeout_sec
    )
