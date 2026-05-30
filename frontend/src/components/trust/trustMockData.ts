export type TrustLevel = 'excellent' | 'good' | 'caution' | 'elevated' | 'high_risk';
export type TrustStatus = 'fresh' | 'stale' | 'pending' | 'failed' | 'mock';

export interface TrustProfile {
  company_id: string;
  trust_score: number;
  trust_level: TrustLevel;
  checked_at: string;
  expires_at: string;
  positives: string[];
  warnings: string[];
  verdict: string;
  report_version: string;
  source: string;
  is_premium: boolean;
  full_report: string | null;
  status: TrustStatus;
}

export const MOCK_PROFILES: TrustProfile[] = [
  {
    company_id: 'company-001',
    trust_score: 85,
    trust_level: 'excellent',
    checked_at: '2026-05-30T09:00:00+04:00',
    expires_at: '2026-05-31T09:00:00+04:00',
    positives: ['Работает 7 лет', 'Официальный сайт подтверждён', 'Нет судебных исков в арбитраже'],
    warnings: [],
    verdict: 'Можно работать',
    report_version: '1.0',
    source: 'mock',
    is_premium: false,
    full_report: null,
    status: 'fresh',
  },
  {
    company_id: 'company-002',
    trust_score: 55,
    trust_level: 'caution',
    checked_at: '2026-05-29T12:00:00+04:00',
    expires_at: '2026-05-30T08:00:00+04:00',
    positives: ['Работает 2 года'],
    warnings: ['Минимальный уставный капитал', 'Официальный сайт не найден'],
    verdict: 'Нужна осторожность',
    report_version: '1.0',
    source: 'mock',
    is_premium: false,
    full_report: null,
    status: 'stale',
  },
  {
    company_id: 'company-003',
    trust_score: 22,
    trust_level: 'high_risk',
    checked_at: '2026-05-28T08:00:00+04:00',
    expires_at: '2026-05-29T08:00:00+04:00',
    positives: [],
    warnings: [
      'Зарегистрирована менее 1 года',
      'Массовый адрес регистрации',
      'Судебные иски в арбитраже',
    ],
    verdict: 'Высокий риск',
    report_version: '1.0',
    source: 'mock',
    is_premium: false,
    full_report: null,
    status: 'fresh',
  },
];

export function getMockProfile(seed: string): TrustProfile {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  }
  return MOCK_PROFILES[Math.abs(hash) % MOCK_PROFILES.length];
}

export function verdictEmoji(level: TrustLevel): string {
  switch (level) {
    case 'excellent':
    case 'good':
      return '🟢';
    case 'caution':
      return '🟡';
    case 'elevated':
      return '🟠';
    case 'high_risk':
      return '🔴';
  }
}

export function levelClass(level: TrustLevel): string {
  return level.replace('_', '-');
}
