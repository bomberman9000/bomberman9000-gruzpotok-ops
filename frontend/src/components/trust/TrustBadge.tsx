import './trust.css';
import { verdictEmoji, levelClass } from './trustMockData';
import type { TrustProfile } from './trustMockData';

interface TrustBadgeProps {
  profile?: TrustProfile | null;
  loading?: boolean;
}

export function TrustBadge({ profile, loading }: TrustBadgeProps) {
  if (loading) {
    return <span className="trust-badge pending">⏳ —</span>;
  }
  if (!profile) {
    return <span className="trust-badge pending">— —</span>;
  }
  const emoji = verdictEmoji(profile.trust_level);
  const cls = levelClass(profile.trust_level);
  return (
    <span className={`trust-badge ${cls}`} title={`Trust Score: ${profile.trust_score}/100 — ${profile.verdict}`}>
      {emoji} {profile.trust_score}
    </span>
  );
}
