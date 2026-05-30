import type { TrustLevel, TrustProfile } from "../../api/types";

export type { TrustLevel };

export function verdictEmoji(level: TrustLevel): string {
  switch (level) {
    case "excellent":
    case "good":
      return "🟢";
    case "caution":
      return "🟡";
    case "elevated":
      return "🟠";
    case "high_risk":
      return "🔴";
  }
}

export function levelClass(level: TrustLevel): string {
  return level.replace("_", "-");
}

export const MOCK_PROFILES: TrustProfile[] = [
  {
    subjectType: "company",
    subjectId: "company-001",
    trustScore: 85,
    trustLevel: "excellent",
    status: "fresh",
    verdict: "Можно работать",
    positives: ["Работает 7 лет", "Официальный сайт подтверждён", "Нет судебных исков в арбитраже"],
    warnings: [],
    checkedAt: "2026-05-30T09:00:00+04:00",
    expiresAt: "2026-05-31T09:00:00+04:00",
    canRefresh: false,
    isPremium: false,
    fullReport: null,
  },
  {
    subjectType: "company",
    subjectId: "company-002",
    trustScore: 55,
    trustLevel: "caution",
    status: "stale",
    verdict: "Нужна осторожность",
    positives: ["Работает 2 года"],
    warnings: ["Минимальный уставный капитал", "Официальный сайт не найден"],
    checkedAt: "2026-05-29T12:00:00+04:00",
    expiresAt: "2026-05-30T08:00:00+04:00",
    canRefresh: false,
    isPremium: false,
    fullReport: null,
  },
  {
    subjectType: "company",
    subjectId: "company-003",
    trustScore: 22,
    trustLevel: "high_risk",
    status: "fresh",
    verdict: "Высокий риск",
    positives: [],
    warnings: [
      "Зарегистрирована менее 1 года",
      "Массовый адрес регистрации",
      "Судебные иски в арбитраже",
    ],
    checkedAt: "2026-05-28T08:00:00+04:00",
    expiresAt: "2026-05-29T08:00:00+04:00",
    canRefresh: false,
    isPremium: false,
    fullReport: null,
  },
];

export function getMockProfile(seed: string): TrustProfile {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  }
  return MOCK_PROFILES[Math.abs(hash) % MOCK_PROFILES.length];
}
