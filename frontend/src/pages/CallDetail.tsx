import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { AIHistoryDetail, TimelineEvent } from "../api/types";
import { CopyButton } from "../components/CopyButton";
import { Modal } from "../components/Modal";
import { CitationsList } from "../components/CitationsList";
import { StatusBadge } from "../components/StatusBadge";
import { TimelineView } from "../components/TimelineView";
import { TransportOrderPdfPanel } from "../components/TransportOrderPdfPanel";
import { useToast } from "../context/ToastContext";
import { REVIEW_REASON_OPTIONS } from "../constants/reviewReasons";

function citationsFromCall(call: Record<string, unknown>) {
  const raw = call.raw_data_json;
  if (!raw || typeof raw !== "object") return [];
  const c = (raw as { citations?: Array<Record<string, unknown>> }).citations;
  if (!Array.isArray(c)) return [];
  return c.map((x) => ({
    title: String(x.title ?? x.source ?? ""),
    snippet: String(x.snippet ?? x.text ?? "").slice(0, 500),
    ref: x.ref ?? x.id,
  }));
}

function DetailBody({
  detail,
  events,
  onFeedback,
  onReload,
}: {
  detail: AIHistoryDetail;
  events: TimelineEvent[];
  onFeedback: (useful: boolean) => void;
  onReload: () => void;
}) {
  const toast = useToast();
  const call = detail.call as Record<string, unknown>;
  const callId = Number(call.id);
  const requestId = String(call.request_id ?? "");
  const [showReject, setShowReject] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [reason, setReason] = useState("");
  const [rejectCodes, setRejectCodes] = useState<string[]>([]);
  const [editCodes, setEditCodes] = useState<string[]>([]);
  const [finalText, setFinalText] = useState(String(call.response_summary ?? ""));

  const toggleCode = (list: string[], setList: (v: string[]) => void, id: string) => {
    setList(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  };

  const runReject = async () => {
    if (!reason.trim()) {
      toast("Укажите причину", "err");
      return;
    }
    try {
      await api.reject(callId, reason.trim(), rejectCodes.length ? rejectCodes : undefined);
      toast("Отклонено");
      setShowReject(false);
      onReload();
    } catch (e) {
      toast((e as Error).message, "err");
    }
  };

  const runEdit = async () => {
    if (!finalText.trim()) {
      toast("Укажите текст", "err");
      return;
    }
    try {
      await api.edit(callId, finalText.trim(), undefined, editCodes.length ? editCodes : undefined);
      toast("Сохранено");
      setShowEdit(false);
      onReload();
    } catch (e) {
      toast((e as Error).message, "err");
    }
  };

  const runAccept = async () => {
    try {
      await api.accept(callId);
      toast("Принято");
      onReload();
    } catch (e) {
      toast((e as Error).message, "err");
    }
  };

  const ru = detail.review_ui as { suggested_text?: string } | undefined;
  const cits = citationsFromCall(call);
  const rev = detail.review as { operator_action?: string; review_reason_codes?: string[] } | null;
  const th = detail.tuning_hints as
    | { likely_primary_area?: string | null; hints?: { area?: string; message?: string; severity?: string }[] }
    | null
    | undefined;

  return (
    <div>
      <p className="muted">
        <Link to="/history">← История</Link>
      </p>
      <h1>Вызов #{callId}</h1>
      <div className="row">
        <StatusBadge value={String(call.normalized_status ?? "")} />
        <span>
          request_id: <code style={{ fontSize: "0.9rem" }}>{requestId}</code>
        </span>
        {requestId && <CopyButton text={requestId} label="Copy request_id" />}
        <Link to={`/calls/by-request/${encodeURIComponent(requestId)}`}>по request</Link>
      </div>

      {rev?.operator_action && (
        <p className="muted" style={{ fontSize: "0.85rem" }}>
          Review: <span className="badge">{rev.operator_action}</span>
          {(rev.review_reason_codes ?? []).map((c) => (
            <span key={c} className="badge" style={{ background: "#2d3748", marginLeft: 4 }}>
              {c}
            </span>
          ))}
        </p>
      )}

      {th && (th.hints?.length ?? 0) > 0 && (
        <div className="card" style={{ marginTop: "0.75rem" }}>
          <div className="label">Likely tuning area</div>
          {th.likely_primary_area && (
            <p style={{ margin: "0.25rem 0", fontWeight: 600 }}>{String(th.likely_primary_area)}</p>
          )}
          <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.1rem", fontSize: "0.9rem" }}>
            {(th.hints ?? []).map((h, i) => (
              <li key={i}>
                [{h.severity}] {h.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      <h2>Кратко</h2>
      <p>{String(call.response_summary ?? "—")}</p>

      <TransportOrderPdfPanel call={call} />

      <div className="row" style={{ marginTop: "1rem" }}>
        <button type="button" className="primary" onClick={runAccept}>
          Принять (review)
        </button>
        <button type="button" className="danger" onClick={() => setShowReject(true)}>
          Отклонить
        </button>
        <button type="button" onClick={() => setShowEdit(true)}>
          Правка текста
        </button>
      </div>

      <h2>Feedback</h2>
      <div className="row">
        <button type="button" className="primary" onClick={() => onFeedback(true)}>
          Полезно
        </button>
        <button type="button" onClick={() => onFeedback(false)}>
          Не полезно
        </button>
      </div>
      <p className="muted" style={{ fontSize: "0.85rem" }}>
        {JSON.stringify(detail.feedback_summary ?? {})}
      </p>

      <h2>Review / UI</h2>
      <pre style={{ fontSize: "0.8rem", overflow: "auto" }}>{JSON.stringify(detail.review ?? {}, null, 2)}</pre>

      <h2>Timeline</h2>
      <TimelineView events={events} />

      <h2>Цитаты</h2>
      {cits.length > 0 && <CopyButton text={JSON.stringify(cits, null, 2)} label="Копировать citations (JSON)" />}
      <CitationsList citations={cits} />

      <h2>raw call (debug)</h2>
      <pre style={{ fontSize: "0.75rem", overflow: "auto", maxHeight: 240 }}>{JSON.stringify(call, null, 2)}</pre>

      {showReject && (
        <Modal title="Отклонить" onClose={() => setShowReject(false)}>
          <label className="stack">
            Причина (обязательно)
            <textarea rows={4} value={reason} onChange={(e) => setReason(e.target.value)} style={{ width: "100%" }} />
          </label>
          <div className="stack" style={{ marginTop: "0.5rem" }}>
            <span className="muted" style={{ fontSize: "0.85rem" }}>
              Нормализованные причины
            </span>
            <div className="row" style={{ flexWrap: "wrap", gap: "0.35rem" }}>
              {REVIEW_REASON_OPTIONS.map((o) => (
                <label key={o.id} style={{ fontSize: "0.85rem" }}>
                  <input
                    type="checkbox"
                    checked={rejectCodes.includes(o.id)}
                    onChange={() => toggleCode(rejectCodes, setRejectCodes, o.id)}
                  />{" "}
                  {o.label}
                </label>
              ))}
            </div>
          </div>
          <div className="modal-actions">
            <button type="button" onClick={() => setShowReject(false)}>
              Отмена
            </button>
            <button type="button" className="danger" onClick={runReject}>
              Отклонить
            </button>
          </div>
        </Modal>
      )}

      {showEdit && (
        <Modal title="Финальный текст" onClose={() => setShowEdit(false)}>
          <label className="stack">
            final_text
            <textarea rows={8} value={finalText} onChange={(e) => setFinalText(e.target.value)} style={{ width: "100%" }} />
          </label>
          <div className="stack" style={{ marginTop: "0.5rem" }}>
            <span className="muted" style={{ fontSize: "0.85rem" }}>
              Почему правка (коды)
            </span>
            <div className="row" style={{ flexWrap: "wrap", gap: "0.35rem" }}>
              {REVIEW_REASON_OPTIONS.map((o) => (
                <label key={o.id} style={{ fontSize: "0.85rem" }}>
                  <input
                    type="checkbox"
                    checked={editCodes.includes(o.id)}
                    onChange={() => toggleCode(editCodes, setEditCodes, o.id)}
                  />{" "}
                  {o.label}
                </label>
              ))}
            </div>
          </div>
          <p className="muted" style={{ fontSize: "0.8rem" }}>
            suggested: {ru?.suggested_text?.slice?.(0, 200) ?? "—"}
          </p>
          <div className="modal-actions">
            <button type="button" onClick={() => setShowEdit(false)}>
              Отмена
            </button>
            <button type="button" className="primary" onClick={runEdit}>
              Сохранить
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

export function CallDetail() {
  const { callId } = useParams<{ callId: string }>();
  const id = Number(callId);
  if (!callId || Number.isNaN(id)) {
    return <div className="error">Неверный id вызова</div>;
  }
  return <CallDetailLoader callId={id} requestId={undefined} />;
}

export function CallByRequest() {
  const { requestId } = useParams<{ requestId: string }>();
  return <CallDetailLoader callId={undefined} requestId={requestId ? decodeURIComponent(requestId) : undefined} />;
}

function CallDetailLoader({ callId, requestId }: { callId?: number; requestId?: string }) {
  const toast = useToast();
  const [detail, setDetail] = useState<AIHistoryDetail | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      const d =
        callId != null && !Number.isNaN(callId)
          ? await api.callDetail(callId)
          : requestId
            ? await api.callByRequest(requestId)
            : await Promise.reject(new Error("no id"));
      setDetail(d);
      const id = Number((d.call as { id?: number }).id);
      if (id) {
        const t = await api.timeline(id);
        setEvents(t.events);
      } else {
        setEvents([]);
      }
    } catch (e) {
      setErr((e as Error).message);
      setDetail(null);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [callId, requestId]);

  useEffect(() => {
    load();
  }, [load]);

  const onFeedback = (useful: boolean) => {
    if (!detail) return;
    const rid = String((detail.call as { request_id?: string }).request_id ?? "");
    api
      .feedback({ request_id: rid, useful })
      .then(() => {
        toast(useful ? "Спасибо, отмечено как полезно" : "Отмечено как не полезно");
        load();
      })
      .catch((e: Error) => toast(e.message, "err"));
  };

  if (loading && !detail) return <p className="muted">Загрузка…</p>;
  if (err) return <div className="error">{err}</div>;
  if (!detail) return <div className="empty">Нет данных</div>;

  return <DetailBody detail={detail} events={events} onFeedback={onFeedback} onReload={load} />;
}
