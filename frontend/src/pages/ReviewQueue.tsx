import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { QueuePanelResponse } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { useToast } from "../context/ToastContext";

const QK = {
  persona: "gp_q_persona",
  scenario: "gp_q_sc",
  status: "gp_q_st",
  reviewed: "gp_q_rev",
  reviewReason: "gp_q_rr",
};

export function ReviewQueue() {
  const toast = useToast();
  const [data, setData] = useState<QueuePanelResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [persona, setPersona] = useState(() => localStorage.getItem(QK.persona) || "");
  const [scenario, setScenario] = useState(() => localStorage.getItem(QK.scenario) || "");
  const [status, setStatus] = useState(() => localStorage.getItem(QK.status) || "");
  const [reviewed, setReviewed] = useState<string>(() => localStorage.getItem(QK.reviewed) || "");
  const [reviewReason, setReviewReason] = useState(() => localStorage.getItem(QK.reviewReason) || "");

  useEffect(() => {
    localStorage.setItem(QK.persona, persona);
    localStorage.setItem(QK.scenario, scenario);
    localStorage.setItem(QK.status, status);
    localStorage.setItem(QK.reviewed, reviewed);
    localStorage.setItem(QK.reviewReason, reviewReason);
  }, [persona, scenario, status, reviewed, reviewReason]);

  const params = useMemo(() => {
    const q = new URLSearchParams();
    if (persona.trim()) q.set("persona", persona.trim());
    if (scenario.trim()) q.set("scenario", scenario.trim());
    if (status.trim()) q.set("status", status.trim());
    if (reviewed === "true") q.set("reviewed", "true");
    if (reviewed === "false") q.set("reviewed", "false");
    if (reviewReason.trim()) q.set("review_reason_code", reviewReason.trim());
    q.set("limit", "50");
    return q;
  }, [persona, scenario, status, reviewed, reviewReason]);

  const load = useCallback(() => {
    setLoading(true);
    api
      .reviewQueuePanel(params)
      .then((d) => {
        setData(d);
        setErr(null);
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [params]);

  useEffect(() => {
    load();
  }, [load]);

  const onAccept = async (callId: number) => {
    try {
      await api.accept(callId);
      toast("Принято");
      load();
    } catch (e) {
      toast((e as Error).message, "err");
    }
  };

  if (loading && !data) return <p className="muted">Загрузка…</p>;
  if (err) return <div className="error">{err}</div>;

  const items = data?.items ?? [];

  return (
    <div>
      <h1>Очередь review</h1>
      <p className="muted">Сортировка по priority на стороне API</p>
      <ErrorBanner message={err || ""} onRetry={load} />

      <div className="row">
        <label>
          Persona{" "}
          <input value={persona} onChange={(e) => setPersona(e.target.value)} placeholder="legal" />
        </label>
        <label>
          Сценарий{" "}
          <input value={scenario} onChange={(e) => setScenario(e.target.value)} placeholder="kind/endpoint" />
        </label>
        <label>
          Status{" "}
          <input value={status} onChange={(e) => setStatus(e.target.value)} placeholder="normalized_status" />
        </label>
        <label>
          Reviewed{" "}
          <select value={reviewed} onChange={(e) => setReviewed(e.target.value)}>
            <option value="">все</option>
            <option value="false">нет</option>
            <option value="true">да</option>
          </select>
        </label>
        <label>
          Review reason code{" "}
          <input
            value={reviewReason}
            onChange={(e) => setReviewReason(e.target.value)}
            placeholder="weak_citations"
            style={{ width: "9rem" }}
          />
        </label>
        <button type="button" className="primary" onClick={load}>
          Обновить
        </button>
      </div>

      {items.length === 0 && !loading && <div className="empty">Пусто</div>}

      {items.map((it, idx) => {
        const raw = it.raw as { call_id?: number };
        const callId = raw.call_id;
        return (
          <div key={idx} className="queue-card">
            <div className="row">
              <strong>{it.title}</strong>
              <span className="badge">{it.persona_badge}</span>
              <span className="badge warn">{it.status_badge}</span>
              {(it.review_reason_badges ?? []).map((b) => (
                <span key={b} className="badge" style={{ background: "#2d3748" }}>
                  {b}
                </span>
              ))}
              <span className="muted">priority {typeof it.priority === "number" ? it.priority.toFixed(1) : it.priority}</span>
            </div>
            <div className="muted">{it.subtitle}</div>
            <div style={{ fontSize: "0.85rem", marginTop: "0.35rem" }}>{(it.reasons || []).join(" · ")}</div>
            <div className="actions">
              {callId != null && (
                <>
                  <Link to={`/calls/${callId}`}>Открыть детали</Link>
                  <button type="button" className="primary" onClick={() => onAccept(callId)}>
                    Принять
                  </button>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
