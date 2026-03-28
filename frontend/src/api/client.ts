import type {
  AIHistoryDetail,
  AIHistoryListItem,
  AnalyticsPanel,
  CasePanel,
  DashboardSummary,
  QueuePanelResponse,
  TimelineEvent,
} from "./types";

const base = () => (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

/** Dev-only: можно задать VITE_INTERNAL_TOKEN в .env.local (не для production secrets). */
function internalTokenHeader(): Record<string, string> {
  const fromEnv = import.meta.env.VITE_INTERNAL_TOKEN;
  if (fromEnv) return { "X-Internal-Token": String(fromEnv) };
  if (typeof sessionStorage !== "undefined") {
    const t = sessionStorage.getItem("internal_token");
    if (t) return { "X-Internal-Token": t };
  }
  return {};
}

function reviewedByHeader(): Record<string, string> {
  const id = localStorage.getItem("operator_id");
  return id ? { "X-Reviewed-By": id } : {};
}

function mergeHeaders(init?: HeadersInit): Headers {
  const h = new Headers(init);
  const it = internalTokenHeader();
  Object.entries(it).forEach(([k, v]) => h.set(k, v));
  return h;
}

function logApiError(path: string, status: number, body: string) {
  console.error("[api]", path, status, body?.slice?.(0, 500) ?? body);
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${base()}${path}`;
  const headers = mergeHeaders(init?.headers);
  if (init?.body && typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(url, { ...init, headers });
  const text = await res.text();
  if (!res.ok) {
    logApiError(path, res.status, text);
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
  if (!text) return {} as T;
  try {
    return JSON.parse(text) as T;
  } catch (e) {
    console.error("[api] JSON parse", path, e);
    throw new Error("Invalid JSON response");
  }
}

export const api = {
  dashboard: () => apiFetch<DashboardSummary>("/api/v1/internal/ai/dashboard"),

  analyticsPanel: (q?: URLSearchParams) =>
    apiFetch<AnalyticsPanel>(`/api/v1/internal/ai/analytics/panel${q?.toString() ? `?${q}` : ""}`),

  reviewQueuePanel: (q?: URLSearchParams) =>
    apiFetch<QueuePanelResponse>(`/api/v1/internal/ai/review-queue/panel${q?.toString() ? `?${q}` : ""}`),

  highPriorityNotifications: () =>
    apiFetch<{ alert_text: string; items: unknown[] }>("/api/v1/internal/ai/notifications/high-priority"),

  panelClaim: (id: string) => apiFetch<CasePanel>(`/api/v1/internal/ai/panels/claims/${encodeURIComponent(id)}`),
  panelFreight: (id: string) =>
    apiFetch<CasePanel>(`/api/v1/internal/ai/panels/freight/${encodeURIComponent(id)}`),
  panelDocument: (id: string) =>
    apiFetch<CasePanel>(`/api/v1/internal/ai/panels/documents/${encodeURIComponent(id)}`),
  panelRequest: (requestId: string) =>
    apiFetch<CasePanel>(`/api/v1/internal/ai/panels/by-request/${encodeURIComponent(requestId)}`),

  timeline: (callId: number) =>
    apiFetch<{ call_id: number; events: TimelineEvent[] }>(`/api/v1/internal/ai/calls/${callId}/timeline`),

  callsList: (q?: URLSearchParams) =>
    apiFetch<AIHistoryListItem[]>(`/api/v1/internal/ai/calls${q?.toString() ? `?${q}` : ""}`),

  callDetail: (id: number) => apiFetch<AIHistoryDetail>(`/api/v1/internal/ai/calls/${id}`),

  callByRequest: (requestId: string) =>
    apiFetch<AIHistoryDetail>(
      `/api/v1/internal/ai/calls/by-request/${encodeURIComponent(requestId)}`
    ),

  feedback: (body: {
    request_id: string;
    useful: boolean;
    comment?: string;
    user_role?: string;
    source_screen?: string;
    reason_codes?: string[];
  }) =>
    apiFetch<{ saved: boolean; feedback_id?: number }>("/api/v1/ai/feedback", {
      method: "POST",
      body: JSON.stringify({
        comment: "",
        user_role: "operator",
        source_screen: "ai-operator-ui",
        reason_codes: [],
        ...body,
      }),
    }),

  accept: (
    callId: number,
    body?: { final_text?: string; operator_comment?: string; reason_codes?: string[] }
  ) =>
    apiFetch<{ ok: boolean }>(`/api/v1/internal/ai/calls/${callId}/accept`, {
      method: "POST",
      headers: mergeHeaders(new Headers({ ...reviewedByHeader() })),
      body: JSON.stringify(body ?? {}),
    }),

  reject: (callId: number, reason: string, reason_codes?: string[]) =>
    apiFetch<{ ok: boolean }>(`/api/v1/internal/ai/calls/${callId}/reject`, {
      method: "POST",
      headers: mergeHeaders(new Headers({ ...reviewedByHeader() })),
      body: JSON.stringify({ reason, reason_codes: reason_codes ?? [] }),
    }),

  edit: (callId: number, final_text: string, operator_comment?: string, reason_codes?: string[]) =>
    apiFetch<{ ok: boolean }>(`/api/v1/internal/ai/calls/${callId}/edit`, {
      method: "POST",
      headers: mergeHeaders(new Headers({ ...reviewedByHeader() })),
      body: JSON.stringify({
        final_text,
        operator_comment: operator_comment ?? null,
        reason_codes: reason_codes ?? [],
      }),
    }),

  exportCallUrl: (callId: number) => `${base()}/api/v1/internal/ai/export/call/${callId}`,
  exportQueueUrl: () => `${base()}/api/v1/internal/ai/export/review-queue?limit=100`,
  exportAnalyticsUrl: () => `${base()}/api/v1/internal/ai/export/analytics`,
  exportProblemCasesUrl: (q?: URLSearchParams) =>
    `${base()}/api/v1/internal/ai/export/problem-cases${q?.toString() ? `?${q}` : ""}`,

  /**
   * POST JSON полей заявки → бинарный PDF (публичный /api/v1/ai, без internal token).
   */
  transportOrderPdf: async (body: Record<string, unknown>) => {
    const url = `${base()}/api/v1/ai/freight/transport-order-pdf`;
    const headers = new Headers({ "Content-Type": "application/json" });
    const res = await fetch(url, { method: "POST", headers, body: JSON.stringify(body) });
    if (!res.ok) {
      const t = await res.text();
      logApiError("/api/v1/ai/freight/transport-order-pdf", res.status, t);
      throw new Error(t?.slice?.(0, 500) || `${res.status}`);
    }
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") ?? "";
    const m = /filename="([^"]+)"/.exec(cd) || /filename=([^;\s]+)/.exec(cd);
    const filename = m?.[1]?.replace(/['"]/g, "") || "zayavka_perevozka.pdf";
    return { blob, filename };
  },
};

export function setInternalToken(token: string | null): void {
  if (token) sessionStorage.setItem("internal_token", token);
  else sessionStorage.removeItem("internal_token");
}

export function uiRequireAuth(): boolean {
  return import.meta.env.VITE_UI_REQUIRE_AUTH === "true";
}

/** Скачивание export endpoint с заголовком internal token (обход <a href>). */
export async function downloadExport(path: string, filename: string): Promise<void> {
  const url = `${base()}${path}`;
  const res = await fetch(url, { headers: mergeHeaders() });
  if (!res.ok) {
    const t = await res.text();
    logApiError(path, res.status, t);
    throw new Error(t || `${res.status}`);
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
