import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ReviewQueue } from "./ReviewQueue";
import * as client from "../api/client";
import { ToastProvider } from "../context/ToastContext";

describe("ReviewQueue", () => {
  beforeEach(() => {
    vi.spyOn(client.api, "reviewQueuePanel").mockResolvedValue({ items: [] });
  });

  it("renders queue title", async () => {
    render(
      <MemoryRouter>
        <ToastProvider>
          <ReviewQueue />
        </ToastProvider>
      </MemoryRouter>
    );
    expect(await screen.findByRole("heading", { name: /Очередь review/i })).toBeInTheDocument();
  });
});
