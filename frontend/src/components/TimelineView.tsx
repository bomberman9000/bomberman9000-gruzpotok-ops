import type { TimelineEvent } from "../api/types";

export function TimelineView({ events }: { events: TimelineEvent[] }) {
  if (!events.length) return <p className="muted">Нет событий</p>;
  return (
    <div className="timeline">
      {events.map((e, i) => (
        <div key={i} className="timeline-item">
          <div>
            <StatusBadgeInline type={e.event_type} />
            <time> {e.timestamp || "—"}</time>
          </div>
          <div>{e.summary}</div>
          <div className="muted" style={{ fontSize: "0.8rem" }}>
            {e.actor}
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusBadgeInline({ type }: { type: string }) {
  return <span className="badge">{type}</span>;
}
