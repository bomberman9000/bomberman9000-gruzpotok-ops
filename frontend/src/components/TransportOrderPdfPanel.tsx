import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";

export type PdfAttachmentHint = {
  heading?: string;
  embed_note?: string;
  download_label?: string;
  download_path?: string;
  http_method?: string;
  request_body_hint?: string;
  size_note?: string;
  page_count_typical?: number;
};

function fieldsFromRawData(raw: Record<string, unknown> | undefined): Record<string, unknown> | null {
  if (!raw || typeof raw !== "object") return null;
  const rr = raw.raw_response;
  if (rr && typeof rr === "object" && "fields" in rr) {
    const f = (rr as { fields?: unknown }).fields;
    if (f && typeof f === "object" && !Array.isArray(f)) return f as Record<string, unknown>;
  }
  return null;
}

function hintFromRawData(raw: Record<string, unknown> | undefined): PdfAttachmentHint | null {
  if (!raw || typeof raw !== "object") return null;
  const pres = raw.presentation as { pdf_attachment_hint?: PdfAttachmentHint } | undefined;
  const h = pres?.pdf_attachment_hint;
  return h && typeof h === "object" ? h : null;
}

/** Тело для повторного PDF из user_input_json (после вызова transport-order-pdf). */
export function pdfBodyFromUserInput(ui: unknown): Record<string, unknown> | null {
  if (!ui || typeof ui !== "object") return null;
  const o = ui as Record<string, unknown>;
  if (o.kind !== "transport_order_pdf") return null;
  const { kind: _k, ...rest } = o;
  return Object.keys(rest).length ? rest : null;
}

function pdfBytesFromStoredRaw(raw: Record<string, unknown> | undefined): number | null {
  if (!raw || typeof raw !== "object") return null;
  const rr = raw.raw_response;
  if (rr && typeof rr === "object" && "pdf_size_bytes" in rr) {
    const n = Number((rr as { pdf_size_bytes?: unknown }).pdf_size_bytes);
    return Number.isFinite(n) && n >= 0 ? n : null;
  }
  return null;
}

/** Только вызовы compose / pdf — иначе null. */
export function TransportOrderPdfPanel({ call }: { call: Record<string, unknown> }) {
  const endpoint = String(call.endpoint ?? "");
  if (endpoint === "transport_order_pdf") {
    return <TransportOrderPdfHistoryPanel call={call} />;
  }
  if (endpoint !== "transport_order_compose") return null;
  return <TransportOrderComposePdfPanel call={call} />;
}

function TransportOrderPdfHistoryPanel({ call }: { call: Record<string, unknown> }) {
  const rawData = call.raw_data_json as Record<string, unknown> | undefined;
  const storedBytes = pdfBytesFromStoredRaw(rawData);
  const summary = typeof rawData?.summary === "string" ? rawData.summary : "";
  const ui = call.user_input_json as Record<string, unknown> | undefined;
  const body = pdfBodyFromUserInput(ui);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ bytes: number; filename: string } | null>(null);

  const revoke = useCallback(() => {
    setPdfUrl((u) => {
      if (u) URL.revokeObjectURL(u);
      return null;
    });
  }, []);

  useEffect(() => () => revoke(), [revoke]);

  const loadPdf = async () => {
    if (!body) {
      setErr("Нет сохранённого тела запроса (user_input_json) для повтора PDF.");
      return;
    }
    setLoading(true);
    setErr(null);
    revoke();
    setMeta(null);
    try {
      const { blob, filename } = await api.transportOrderPdf(body);
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
      setMeta({ bytes: blob.size, filename });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const download = () => {
    if (!pdfUrl || !meta) return;
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = meta.filename;
    a.click();
  };

  const kbStored = storedBytes != null ? (storedBytes / 1024).toFixed(1) : null;

  return (
    <div className="card pdf-panel" style={{ marginTop: "0.75rem" }}>
      <h2 className="pdf-panel-title">PDF заявки (из лога вызова)</h2>
      {summary ? (
        <p className="muted pdf-panel-meta">{summary}</p>
      ) : (
        <p className="muted pdf-panel-meta">Бинарный ответ зафиксирован в метаданных вызова.</p>
      )}
      <div className="row pdf-panel-actions">
        {kbStored != null && (
          <span className="muted pdf-panel-meta" data-testid="pdf-stored-kb">
            Размер в логе: {kbStored} КБ
          </span>
        )}
        <span className="muted pdf-panel-meta">Страниц (типично): 1</span>
      </div>
      {body ? (
        <div className="row pdf-panel-actions">
          <button type="button" className="primary" disabled={loading} onClick={loadPdf}>
            {loading ? "Загрузка…" : "Показать PDF снова"}
          </button>
          {pdfUrl && meta && (
            <>
              <button type="button" onClick={download}>
                Скачать файл
              </button>
              <span className="muted pdf-panel-meta">Сейчас: {(meta.bytes / 1024).toFixed(1)} КБ</span>
            </>
          )}
        </div>
      ) : (
        <p className="muted pdf-panel-meta">Повтор PDF недоступен — нет полей в user_input_json.</p>
      )}
      {err && (
        <p className="error pdf-panel-err" role="alert">
          {err}
        </p>
      )}
      {pdfUrl && (
        <div className="pdf-preview-wrap">
          <iframe title="PDF preview" src={pdfUrl} />
        </div>
      )}
    </div>
  );
}

function TransportOrderComposePdfPanel({ call }: { call: Record<string, unknown> }) {
  const rawData = call.raw_data_json as Record<string, unknown> | undefined;
  const fields = fieldsFromRawData(rawData);
  const hint = hintFromRawData(rawData);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [meta, setMeta] = useState<{ bytes: number; filename: string } | null>(null);

  const revoke = useCallback(() => {
    setPdfUrl((u) => {
      if (u) URL.revokeObjectURL(u);
      return null;
    });
  }, []);

  useEffect(() => () => revoke(), [revoke]);

  const loadPdf = async () => {
    if (!fields || Object.keys(fields).length === 0) {
      setErr("Нет полей raw_response.fields для PDF");
      return;
    }
    setLoading(true);
    setErr(null);
    revoke();
    setMeta(null);
    try {
      const body: Record<string, unknown> = {
        pdf_engine: "fpdf",
        pdf_template: "dogovor_zayavka",
        ...fields,
      };
      const { blob, filename } = await api.transportOrderPdf(body);
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
      setMeta({ bytes: blob.size, filename });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const download = () => {
    if (!pdfUrl || !meta) return;
    const a = document.createElement("a");
    a.href = pdfUrl;
    a.download = meta.filename;
    a.click();
  };

  if (!fields || !Object.keys(fields).some((k) => String(fields[k] ?? "").trim())) {
    return (
      <div className="card pdf-panel" style={{ marginTop: "0.75rem" }}>
        <div className="label">Договор-заявка (PDF)</div>
        <p className="muted pdf-panel-meta" style={{ margin: "0.35rem 0 0" }}>
          Нет заполненных полей в сохранённом ответе — PDF недоступен.
        </p>
      </div>
    );
  }

  const title = hint?.heading ?? "Договор-заявка на перевозку груза";
  const pages = hint?.page_count_typical ?? 1;

  return (
    <div className="card pdf-panel" style={{ marginTop: "0.75rem" }}>
      <h2 className="pdf-panel-title">{title}</h2>
      {hint?.embed_note && <p className="muted pdf-panel-meta">{hint.embed_note}</p>}
      <div className="row pdf-panel-actions">
        <button type="button" className="primary" disabled={loading} onClick={loadPdf}>
          {loading ? "Загрузка PDF…" : "Показать PDF"}
        </button>
        {pdfUrl && meta && (
          <>
            <button type="button" onClick={download}>
              {hint?.download_label ?? "Скачать файл"}
            </button>
            <span className="muted pdf-panel-meta">Вес: {(meta.bytes / 1024).toFixed(1)} КБ</span>
            <span className="muted pdf-panel-meta">Страниц (типично): {pages}</span>
          </>
        )}
      </div>
      {err && (
        <p className="error pdf-panel-err" role="alert">
          {err}
        </p>
      )}
      {pdfUrl && (
        <div className="pdf-preview-wrap">
          <iframe title="PDF preview" src={pdfUrl} />
        </div>
      )}
      {hint?.request_body_hint && <p className="muted pdf-panel-hint">{hint.request_body_hint}</p>}
    </div>
  );
}
