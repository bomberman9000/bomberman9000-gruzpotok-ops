import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { api } from "./client";

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: () => Promise.resolve(JSON.stringify({ ok: true })),
      })
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("dashboard calls /api/v1/internal/ai/dashboard", async () => {
    await api.dashboard();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/internal/ai/dashboard"),
      expect.anything()
    );
  });

  it("feedback posts JSON body", async () => {
    await api.feedback({ request_id: "req-1234", useful: true });
    expect(fetch).toHaveBeenCalled();
    const [, init] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toMatchObject({ request_id: "req-1234", useful: true });
  });
});
