import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "./Dashboard";
import * as client from "../api/client";

describe("Dashboard", () => {
  beforeEach(() => {
    vi.spyOn(client.api, "dashboard").mockResolvedValue({
      total_calls_24h: 1,
      total_calls_7d: 2,
      review_queue_count: 0,
      pending_high_priority_count: 0,
      insufficient_data_count_24h: 0,
      unavailable_count_24h: 0,
      negative_feedback_count_7d: 0,
      edited_or_rejected_count_7d: 0,
      top_personas: [],
      top_scenarios: [],
      top_risk_panels: [],
      health_snapshot: {},
      period: {},
    });
    vi.spyOn(client.api, "analyticsPanel").mockResolvedValue({
      summary_cards: [],
      charts_data: {
        by_persona: { labels: [], values: [] },
        by_endpoint: { labels: [], values: [] },
        by_status: { labels: [], values: [] },
      },
      top_negative_patterns: [],
      top_positive_patterns: [],
      review_outcomes: [],
      risks_and_notes: [],
    });
  });

  it("renders heading", async () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );
    expect(await screen.findByRole("heading", { name: /Dashboard/i })).toBeInTheDocument();
  });
});
