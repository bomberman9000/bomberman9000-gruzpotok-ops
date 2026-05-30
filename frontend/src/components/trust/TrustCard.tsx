import "./trust.css";
import type { TrustProfile } from "../../api/types";
import { verdictEmoji, levelClass } from "./trustMockData";

interface TrustCardProps {
  profile?: TrustProfile | null;
  loading?: boolean;
  isPremium?: boolean;
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("ru-RU", {
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function TrustCardLoading() {
  return (
    <div className="trust-card">
      <div className="trust-card-header">
        <h4 className="trust-card-title">🛡 Trust Score</h4>
      </div>
      <div className="trust-card-state">
        <p>⏳ Проверяем…</p>
        <p style={{ fontSize: "0.78rem" }}>обычно 30–60 сек</p>
      </div>
    </div>
  );
}

function TrustCardEmpty() {
  return (
    <div className="trust-card">
      <div className="trust-card-header">
        <h4 className="trust-card-title">🛡 Trust Score</h4>
      </div>
      <div className="trust-card-state">
        <p>Проверка ещё не проводилась</p>
        <button type="button" className="trust-refresh-btn">Запросить проверку</button>
      </div>
    </div>
  );
}

function TrustCardFailed() {
  return (
    <div className="trust-card">
      <div className="trust-card-header">
        <h4 className="trust-card-title">🛡 Trust Score</h4>
      </div>
      <div className="trust-card-state">
        <p>⚠ Не удалось проверить</p>
        <button type="button" className="trust-refresh-btn">Попробовать снова</button>
      </div>
    </div>
  );
}

export function TrustCard({ profile, loading, isPremium = false }: TrustCardProps) {
  if (loading) return <TrustCardLoading />;
  if (!profile) return <TrustCardEmpty />;
  if (profile.status === "pending") return <TrustCardLoading />;
  if (profile.status === "failed") return <TrustCardFailed />;
  if (profile.status === "empty") return <TrustCardEmpty />;

  const isStale = profile.status === "stale";
  const level = profile.trustLevel!;
  const cls = levelClass(level);
  const emoji = verdictEmoji(level);

  return (
    <div className="trust-card">
      <div className="trust-card-header">
        <h4 className="trust-card-title">
          🛡 Trust Score
          <button
            type="button"
            className="trust-tooltip-btn"
            data-tip="Что такое Trust Score?"
            aria-label="Справка о Trust Score"
          >
            ?
          </button>
        </h4>
        {isStale && <span className="trust-stale-badge">🕐 Данные устарели</span>}
      </div>

      <div
        className="trust-score-row"
        role="progressbar"
        aria-valuenow={profile.trustScore ?? 0}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="trust-progress">
          <div
            className={`trust-progress-bar ${cls}`}
            style={{ width: `${profile.trustScore ?? 0}%` }}
          />
        </div>
        <span className="trust-score-value">{profile.trustScore}/100</span>
      </div>

      <div className={`trust-verdict ${cls}`}>
        {emoji} {profile.verdict}
      </div>

      {profile.positives.length > 0 && (
        <ul className="trust-list positives">
          {profile.positives.slice(0, 3).map((p) => (
            <li key={p}>✓ {p}</li>
          ))}
        </ul>
      )}

      {profile.warnings.length > 0 && (
        <ul className="trust-list warnings">
          {profile.warnings.slice(0, 3).map((w) => (
            <li key={w}>⚠ {w}</li>
          ))}
        </ul>
      )}

      {!isPremium && (
        <a href="/pricing" className="trust-cta">
          Подробный отчёт 🔒 Premium
        </a>
      )}

      {profile.checkedAt && (
        <div className={`trust-date ${isStale ? "stale" : ""}`}>
          Проверено: {formatDate(profile.checkedAt)}
          {isStale && " · устарело"}
        </div>
      )}
    </div>
  );
}
