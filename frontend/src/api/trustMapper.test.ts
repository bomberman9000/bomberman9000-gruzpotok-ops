import { describe, it, expect } from "vitest";
import { mapTrustProfile } from "./trustMapper";

const RAW = {
  subject_type: "company",
  subject_id: "7712345678",
  trust_score: 85,
  trust_level: "excellent",
  status: "fresh",
  verdict: "Можно работать",
  positives: ["Работает 7 лет"],
  warnings: [],
  checked_at: "2026-05-30T09:00:00+04:00",
  expires_at: "2026-05-31T09:00:00+04:00",
  can_refresh: false,
  is_premium: false,
  full_report: null,
};

describe("mapTrustProfile", () => {
  it("maps snake_case to camelCase", () => {
    const p = mapTrustProfile(RAW);
    expect(p.subjectType).toBe("company");
    expect(p.subjectId).toBe("7712345678");
    expect(p.trustScore).toBe(85);
    expect(p.trustLevel).toBe("excellent");
    expect(p.status).toBe("fresh");
    expect(p.verdict).toBe("Можно работать");
    expect(p.positives).toEqual(["Работает 7 лет"]);
    expect(p.warnings).toEqual([]);
    expect(p.checkedAt).toBe("2026-05-30T09:00:00+04:00");
    expect(p.expiresAt).toBe("2026-05-31T09:00:00+04:00");
    expect(p.canRefresh).toBe(false);
    expect(p.isPremium).toBe(false);
    expect(p.fullReport).toBeNull();
  });

  it("handles null trust_level", () => {
    const p = mapTrustProfile({ ...RAW, trust_level: null });
    expect(p.trustLevel).toBeNull();
  });

  it("handles null trust_score", () => {
    const p = mapTrustProfile({ ...RAW, trust_score: null });
    expect(p.trustScore).toBeNull();
  });

  it("defaults positives/warnings to empty arrays when missing", () => {
    const p = mapTrustProfile({ ...RAW, positives: undefined as never, warnings: undefined as never });
    expect(p.positives).toEqual([]);
    expect(p.warnings).toEqual([]);
  });

  it("maps empty status correctly", () => {
    const p = mapTrustProfile({ ...RAW, status: "empty", trust_score: null, trust_level: null });
    expect(p.status).toBe("empty");
  });
});
