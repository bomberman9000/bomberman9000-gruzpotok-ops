import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { CasePanel } from "../api/types";
import { CitationsList } from "../components/CitationsList";
import { StatusBadge } from "../components/StatusBadge";

export function CasePanelPage() {
  const { kind, entityId } = useParams<{ kind: string; entityId: string }>();
  const [panel, setPanel] = useState<CasePanel | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!kind || !entityId) return;
    setLoading(true);
    const id = decodeURIComponent(entityId);
    const load =
      kind === "claim"
        ? api.panelClaim(id)
        : kind === "freight"
          ? api.panelFreight(id)
          : kind === "document"
            ? api.panelDocument(id)
            : kind === "request"
              ? api.panelRequest(id)
              : Promise.reject(new Error("unknown kind"));
    load
      .then(setPanel)
      .catch((e: Error) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [kind, entityId]);

  if (loading) return <p className="muted">Загрузка панели…</p>;
  if (err) return <div className="error">{err}</div>;
  if (!panel) return <div className="empty">Нет данных</div>;

  const header = panel.header as Record<string, string | undefined>;
  const fid = panel.primary_call_id;

  return (
    <div>
      <h1>{String(header.title ?? panel.panel_kind)}</h1>
      <p className="muted">
        {String(header.subtitle ?? "")} · request: {String(header.request_id ?? "—")}
      </p>
      <div className="row">
        <StatusBadge value={String(panel.status_badge)} />
        {fid != null && <Link to={`/calls/${fid}`}>Детали вызова #{fid}</Link>}
      </div>

      <h2>Кратко</h2>
      <p>{panel.summary ?? "—"}</p>

      <h2>AI результат</h2>
      <pre
        style={{
          background: "var(--surface)",
          padding: "0.75rem",
          borderRadius: 8,
          overflow: "auto",
          fontSize: "0.85rem",
        }}
      >
        {JSON.stringify(panel.ai_result, null, 2)}
      </pre>

      {(panel.warnings?.length ?? 0) > 0 && (
        <>
          <h2>Предупреждения</h2>
          <ul>
            {panel.warnings.map((w, i) => (
              <li key={i}>
                [{w.code}] {w.message}
              </li>
            ))}
          </ul>
        </>
      )}

      <h2>Следующие шаги</h2>
      <ul>
        {panel.next_steps.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>

      <h2>Цитаты</h2>
      <CitationsList citations={panel.citations} />

      <h2>Feedback</h2>
      <pre style={{ fontSize: "0.85rem" }}>{JSON.stringify(panel.feedback_state, null, 2)}</pre>

      <h2>Review</h2>
      <pre style={{ fontSize: "0.85rem" }}>{JSON.stringify(panel.review_state, null, 2)}</pre>

      <h2>Действия</h2>
      <ul>
        {(panel.operator_actions as { id?: string; label?: string; path?: string }[]).map((a, i) => (
          <li key={i}>
            {a.label} — <code>{a.path}</code>
          </li>
        ))}
      </ul>
    </div>
  );
}
