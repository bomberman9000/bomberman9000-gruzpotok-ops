import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AnalyticsPanel } from "../api/types";
import { ErrorBanner } from "../components/ErrorBanner";

export function Analytics() {
  const [panel, setPanel] = useState<AnalyticsPanel | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setErr(null);
    setLoading(true);
    api
      .analyticsPanel()
      .then(setPanel)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <p className="muted">Загрузка…</p>;
  if (err) return <ErrorBanner message={err} onRetry={load} />;
  if (!panel) return <div className="empty">Нет данных</div>;

  const bar = (labels: string[], values: number[]) => {
    const m = Math.max(1, ...values, 0);
    return (
      <div className="stack">
        {labels.map((lb, i) => (
          <div key={lb + i} className="chart-row">
            <span style={{ minWidth: 100, fontSize: "0.8rem" }}>{lb || "—"}</span>
            <div className="chart-bar">
              <span style={{ width: `${(values[i] / m) * 100}%` }} />
            </div>
            <span>{values[i]}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div>
      <h1>Аналитика</h1>
      <h2>Карточки</h2>
      <div className="grid-cards">
        {panel.summary_cards.map((c) => (
          <div key={c.id} className="card">
            <div className="label">{c.label}</div>
            <div className="value">
              {c.value == null
                ? "—"
                : c.format === "percent"
                  ? `${(Number(c.value) * 100).toFixed(1)}%`
                  : String(c.value)}
            </div>
          </div>
        ))}
      </div>

      <h2>По persona</h2>
      {bar(panel.charts_data.by_persona.labels, panel.charts_data.by_persona.values)}

      <h2>По endpoint</h2>
      {bar(panel.charts_data.by_endpoint.labels, panel.charts_data.by_endpoint.values)}

      <h2>По статусу</h2>
      {bar(panel.charts_data.by_status.labels, panel.charts_data.by_status.values)}

      <h2>Негативные паттерны</h2>
      <ul>
        {panel.top_negative_patterns.map((x, i) => (
          <li key={i}>
            {x.endpoint} / {x.persona}: {x.count}
          </li>
        ))}
      </ul>

      <h2>Позитивные паттерны</h2>
      <ul>
        {panel.top_positive_patterns.map((x, i) => (
          <li key={i}>
            {x.endpoint} / {x.persona}: {x.count}
          </li>
        ))}
      </ul>

      <h2>Исходы review</h2>
      <ul>
        {panel.review_outcomes.map((x) => (
          <li key={x.action}>
            {x.action}: {x.count}
          </li>
        ))}
      </ul>

      <h2>Риски / заметки</h2>
      <ul>
        {panel.risks_and_notes.map((r, i) => (
          <li key={i}>
            [{r.level}] {r.code}: {r.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
