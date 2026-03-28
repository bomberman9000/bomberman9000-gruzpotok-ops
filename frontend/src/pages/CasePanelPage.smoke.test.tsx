import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { CasePanelPage } from "./CasePanelPage";
import * as client from "../api/client";

describe("CasePanelPage", () => {
  beforeEach(() => {
    vi.spyOn(client.api, "panelClaim").mockResolvedValue({
      panel_kind: "claim",
      header: { title: "test" },
      status_badge: "ok",
      summary: null,
      ai_result: {},
      citations: [],
      feedback_state: { items: [], summary: {} },
      review_state: null,
      operator_actions: [],
      history_refs: {},
      warnings: [],
      next_steps: [],
    });
  });

  it("renders panel", async () => {
    render(
      <MemoryRouter
        initialEntries={["/panels/claim/x1"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/panels/:kind/:entityId" element={<CasePanelPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(await screen.findByText("test")).toBeInTheDocument();
  });
});
