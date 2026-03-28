import type { CasePanel } from "../api/types";

export function CitationsList({ citations }: { citations: CasePanel["citations"] }) {
  if (!citations?.length) return <p className="muted">Нет цитат</p>;
  return (
    <div className="stack">
      {citations.map((c, i) => (
        <div key={i} className="citation">
          {c.title && <strong>{c.title}</strong>}
          {c.snippet && <div>{c.snippet}</div>}
        </div>
      ))}
    </div>
  );
}
