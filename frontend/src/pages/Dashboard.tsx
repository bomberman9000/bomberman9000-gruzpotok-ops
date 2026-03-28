import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, downloadExport } from "../api/client";
import type { AnalyticsPanel, DashboardSummary } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";

export function Dashboard() {
  const [dash, setDash] = useState<DashboardSummary | null>(null);
  const [panel, setPanel] = useState<AnalyticsPanel | null>(null);
  const [hp, setHp] = useState<{ alert_text?: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([api.dashboard(), api.analyticsPanel(), api.highPriorityNotifications().catch(() => null)])
      .then(([d, p, h]) => {
        if (!cancelled) {
          setDash(d);
          setPanel(p);
          setHp(h as { alert_text?: string } | null);
          setErr(null);
        }
      })
      .catch((e: Error) => {
        if (!cancelled) setErr(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <p className="muted">Загрузка…</p>;
  if (err) return <ErrorBanner message={err} onRetry={() => window.location.reload()} />;
  if (!dash) return <div className="empty">Нет данных</div>;

  const hs = dash.health_snapshot as Record<string, unknown>;

  return (
    <div>
      <h1>Dashboard</h1>
      <p className="muted">Сводка по AI-вызовам и очереди оператора</p>

      <div className="row" style={{ marginBottom: "1rem" }}>
        <Link to="/queue">→ Очередь review</Link>
        <span className="muted">|</span>
        <Link to="/analytics">→ Аналитика</Link>
        <span className="muted">|</span>
        <Link to="/history">→ История вызовов</Link>
      </div>

      {hp?.alert_text && (
        <div className="card" style={{ marginBottom: "1rem" }}>
          <div className="label">High priority (preview)</div>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem", margin: "0.5rem 0 0" }}>{hp.alert_text}</pre>
        </div>
      )}

      <div className="row" style={{ marginBottom: "1rem" }}>
        <span className="muted">Экспорт JSON:</span>
        <button
          type="button"
          onClick={() => downloadExport("/api/v1/internal/ai/export/analytics", "ai-analytics.json")}
        >
          analytics
        </button>
        <button
          type="button"
          onClick={() => downloadExport("/api/v1/internal/ai/export/review-queue?limit=100", "review-queue.json")}
        >
          review-queue
        </button>
        <button
          type="button"
          onClick={() =>
            downloadExport("/api/v1/internal/ai/export/problem-cases?limit=200", "ai-problem-cases.json")
          }
        >
          problem-cases
        </button>
      </div>

      <h2>Ключевые метрики</h2>
      <div className="grid-cards">
        <div className="card">
          <div className="label">Вызовы 24h</div>
          <div className="value">{dash.total_calls_24h}</div>
        </div>
        <div className="card">
          <div className="label">Вызовы 7d</div>
          <div className="value">{dash.total_calls_7d}</div>
        </div>
        <div className="card">
          <div className="label">Очередь review</div>
          <div className="value">{dash.review_queue_count}</div>
        </div>
        <div className="card">
          <div className="label">High priority (без review)</div>
          <div className="value">{dash.pending_high_priority_count}</div>
        </div>
        <div className="card">
          <div className="label">Insufficient 24h</div>
          <div className="value">{dash.insufficient_data_count_24h}</div>
        </div>
        <div className="card">
          <div className="label">Unavailable 24h</div>
          <div className="value">{dash.unavailable_count_24h}</div>
        </div>
        <div className="card">
          <div className="label">Негативный feedback 7d</div>
          <div className="value">{dash.negative_feedback_count_7d}</div>
        </div>
        <div className="card">
          <div className="label">Edited / rejected 7d</div>
          <div className="value">{dash.edited_or_rejected_count_7d}</div>
        </div>
      </div>

      <h2>Health</h2>
      <div className="card stack">
        <div>
          RAG доступен: <strong>{String(hs?.last_rag_available ?? "—")}</strong>
        </div>
        {hs?.last_rag_error != null && (
          <div className="muted">Последняя ошибка RAG: {String(hs.last_rag_error)}</div>
        )}
        <div className="muted">Всего вызовов (процесс): {String(hs?.total_ai_calls ?? "—")}</div>
      </div>

      <h2>Топ persona (7d)</h2>
      <ul>
        {dash.top_personas.map((x) => (
          <li key={x.persona}>
            {x.persona}: {x.count}
          </li>
        ))}
      </ul>

      <h2>Топ сценарии (7d)</h2>
      <ul>
        {dash.top_scenarios.map((x) => (
          <li key={x.scenario}>
            {x.scenario}: {x.count}
          </li>
        ))}
      </ul>

      {panel && (
        <>
          <h2>Карточки аналитики (панель)</h2>
          <div className="grid-cards">
            {panel.summary_cards.map((c) => (
              <div key={c.id} className="card">
                <div className="label">{c.label}</div>
                <div className="value">
                  {c.value == null ? "—" : c.format === "percent" ? `${(Number(c.value) * 100).toFixed(1)}%` : String(c.value)}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
