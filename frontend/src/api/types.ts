/** DTOs — подмножество полей backend JSON */

export interface DashboardSummary {
  total_calls_24h: number;
  total_calls_7d: number;
  review_queue_count: number;
  pending_high_priority_count: number;
  insufficient_data_count_24h: number;
  unavailable_count_24h: number;
  negative_feedback_count_7d: number;
  edited_or_rejected_count_7d: number;
  top_personas: { persona: string; count: number }[];
  top_scenarios: { scenario: string; count: number }[];
  top_risk_panels: { endpoint: string; persona: string; risk_level: string; count: number }[];
  health_snapshot: Record<string, unknown>;
  period: Record<string, unknown>;
}

export interface SummaryCard {
  id: string;
  label: string;
  value: number | null;
  format: string;
}

export interface AnalyticsPanel {
  summary_cards: SummaryCard[];
  charts_data: {
    by_persona: { labels: string[]; values: number[] };
    by_endpoint: { labels: string[]; values: number[] };
    by_status: { labels: string[]; values: number[] };
  };
  top_negative_patterns: { endpoint?: string; persona?: string; count: number }[];
  top_positive_patterns: { endpoint?: string; persona?: string; count: number }[];
  review_outcomes: { action: string; count: number }[];
  risks_and_notes: { level?: string; code?: string; message?: string }[];
  raw_analytics?: Record<string, unknown>;
}

export interface QueuePanelItem {
  title: string;
  subtitle: string;
  priority: number;
  persona_badge: string;
  scenario_label: string;
  status_badge: string;
  review_reason_badges?: string[];
  reasons: string[];
  quick_actions: { id: string; label: string; method: string; path: string }[];
  raw: Record<string, unknown>;
}

export interface QueuePanelResponse {
  items: QueuePanelItem[];
  total_in_pool?: number;
  filters?: Record<string, unknown>;
}

export interface CasePanel {
  panel_kind: string;
  header: Record<string, unknown>;
  status_badge: string;
  summary: string | null;
  ai_result: Record<string, unknown>;
  citations: { title?: string; snippet?: string; ref?: unknown }[];
  feedback_state: { items: unknown[]; summary: Record<string, number> };
  review_state: Record<string, unknown> | null;
  operator_actions: unknown[];
  history_refs: Record<string, unknown>;
  warnings: { level?: string; code?: string; message?: string }[];
  next_steps: string[];
  effective_outcome?: string;
  primary_call_id?: number;
}

export interface TimelineEvent {
  event_type: string;
  timestamp: string | null;
  actor: string;
  summary: string;
  metadata: Record<string, unknown>;
}

export interface AIHistoryListItem {
  id: number;
  created_at: string;
  request_id: string;
  endpoint: string;
  persona?: string | null;
  mode?: string | null;
  normalized_status: string;
  llm_invoked?: boolean | null;
  citations_count: number;
  response_summary?: string | null;
  latency_ms: number;
  is_error: boolean;
  user_input_json: Record<string, unknown>;
  review_operator_action?: string | null;
  review_reason_codes?: string[];
}

export interface AIHistoryDetail {
  call: Record<string, unknown>;
  feedback: Record<string, unknown>[];
  entity: Record<string, unknown>;
  review?: Record<string, unknown> | null;
  feedback_summary?: Record<string, number>;
  effective_outcome?: string | null;
  human_ai_diff?: boolean | null;
  review_ui?: Record<string, unknown> | null;
  tuning_hints?: Record<string, unknown> | null;
}
