import "./trust.css";
import type { TrustProfile } from "../../api/types";
import { verdictEmoji, levelClass } from "./trustMockData";

interface TrustBadgeProps {
  profile?: TrustProfile | null;
  loading?: boolean;
}

export function TrustBadge({ profile, loading }: TrustBadgeProps) {
  if (loading) {
    return <span className="trust-badge pending">⏳ —</span>;
  }
  if (!profile || !profile.trustLevel) {
    return <span className="trust-badge pending">— —</span>;
  }
  const emoji = verdictEmoji(profile.trustLevel);
  const cls = levelClass(profile.trustLevel);
  return (
    <span
      className={`trust-badge ${cls}`}
      title={`Trust Score: ${profile.trustScore}/100 — ${profile.verdict}`}
    >
      {emoji} {profile.trustScore}
    </span>
  );
}
