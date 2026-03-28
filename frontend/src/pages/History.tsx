import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { AIHistoryListItem } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";
import { StatusBadge } from "../components/StatusBadge";

const K = {
  q: "gp_hist_q",
  persona: "gp_hist_persona",
  endpoint: "gp_hist_ep",
  status: "gp_hist_st",
  llm: "gp_hist_llm",
  df: "gp_hist_df",
  dt: "gp_hist_dt",
  rr: "gp_hist_rr",
};

export function History() {
  const [rows, setRows] = useState<AIHistoryListItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState(() => localStorage.getItem(K.q) || "");
  const [persona, setPersona] = useState(() => localStorage.getItem(K.persona) || "");
  const [endpoint, setEndpoint] = useState(() => localStorage.getItem(K.endpoint) || "");
  const [status, setStatus] = useState(() => localStorage.getItem(K.status) || "");
  const [llm, setLlm] = useState<string>(() => localStorage.getItem(K.llm) || "");
  const [dateFrom, setDateFrom] = useState(() => localStorage.getItem(K.df) || "");
  const [dateTo, setDateTo] = useState(() => localStorage.getItem(K.dt) || "");
  const [reviewReason, setReviewReason] = useState(() => localStorage.getItem(K.rr) || "");

  useEffect(() => {
    localStorage.setItem(K.q, q);
    localStorage.setItem(K.persona, persona);
    localStorage.setItem(K.endpoint, endpoint);
    localStorage.setItem(K.status, status);
    localStorage.setItem(K.llm, llm);
    localStorage.setItem(K.df, dateFrom);
    localStorage.setItem(K.dt, dateTo);
    localStorage.setItem(K.rr, reviewReason);
  }, [q, persona, endpoint, status, llm, dateFrom, dateTo, reviewReason]);

  const load = useCallback(() => {
    setLoading(true);
    const p = new URLSearchParams();
    if (q.trim()) p.set("q", q.trim());
    if (persona.trim()) p.set("persona", persona.trim());
    if (endpoint.trim()) p.set("endpoint", endpoint.trim());
    if (status.trim()) p.set("status", status.trim());
    if (llm === "true") p.set("llm_invoked", "true");
    if (llm === "false") p.set("llm_invoked", "false");
    if (dateFrom) p.set("date_from", dateFrom);
    if (dateTo) p.set("date_to", dateTo);
    if (reviewReason.trim()) p.set("review_reason_code", reviewReason.trim());
    p.set("limit", "100");
    api
      .callsList(p)
      .then((r) => {
        setRows(r);
        setErr(null);
      })
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [q, persona, endpoint, status, llm, dateFrom, dateTo, reviewReason]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <h1>История AI-вызовов</h1>
      <ErrorBanner message={err || ""} onRetry={load} />
      <div className="row">
        <label>
          q <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="summary / request_id" />
        </label>
        <label>
          persona <input value={persona} onChange={(e) => setPersona(e.target.value)} />
        </label>
        <label>
          endpoint <input value={endpoint} onChange={(e) => setEndpoint(e.target.value)} />
        </label>
        <label>
          status <input value={status} onChange={(e) => setStatus(e.target.value)} />
        </label>
        <label>
          llm{" "}
          <select value={llm} onChange={(e) => setLlm(e.target.value)}>
            <option value="">все</option>
            <option value="true">да</option>
            <option value="false">нет</option>
          </select>
        </label>
        <label>
          date_from <input type="datetime-local" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label>
          date_to <input type="datetime-local" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </label>
        <label>
          review_reason <input value={reviewReason} onChange={(e) => setReviewReason(e.target.value)} placeholder="code" />
        </label>
        <button type="button" className="primary" onClick={load}>
          Найти
        </button>
      </div>

      {loading && <p className="muted">Загрузка…</p>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>id</th>
              <th>created</th>
              <th>request_id</th>
              <th>endpoint</th>
              <th>persona</th>
              <th>status</th>
              <th>review</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td style={{ whiteSpace: "nowrap", fontSize: "0.8rem" }}>{r.created_at}</td>
                <td>
                  <Link to={`/calls/by-request/${encodeURIComponent(r.request_id)}`}>{r.request_id}</Link>
                </td>
                <td>{r.endpoint}</td>
                <td>{r.persona ?? "—"}</td>
                <td>
                  <StatusBadge value={r.normalized_status} />
                </td>
                <td style={{ fontSize: "0.75rem", maxWidth: "12rem" }}>
                  {r.review_operator_action && <span className="badge">{r.review_operator_action}</span>}{" "}
                  {(r.review_reason_codes ?? []).slice(0, 3).map((c) => (
                    <span key={c} className="badge" style={{ background: "#2d3748" }}>
                      {c}
                    </span>
                  ))}
                </td>
                <td>
                  <Link to={`/calls/${r.id}`}>detail</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
