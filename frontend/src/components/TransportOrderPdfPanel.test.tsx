import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import * as client from "../api/client";
import { TransportOrderPdfPanel, pdfBodyFromUserInput } from "./TransportOrderPdfPanel";

describe("pdfBodyFromUserInput", () => {
  it("strips kind and keeps fields", () => {
    const b = pdfBodyFromUserInput({
      kind: "transport_order_pdf",
      customer_name: "ООО",
      cargo_name: "груз",
    });
    expect(b).toEqual({ customer_name: "ООО", cargo_name: "груз" });
  });

  it("returns null for wrong kind", () => {
    expect(pdfBodyFromUserInput({ kind: "transport_order_compose" })).toBeNull();
  });
});

describe("TransportOrderPdfPanel", () => {
  beforeEach(() => {
    vi.spyOn(client.api, "transportOrderPdf").mockResolvedValue({
      blob: new Blob(["%PDF-1.4\n"], { type: "application/pdf" }),
      filename: "zayavka.pdf",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows stored PDF size for transport_order_pdf endpoint", () => {
    render(
      <TransportOrderPdfPanel
        call={{
          endpoint: "transport_order_pdf",
          raw_data_json: {
            summary: "PDF договора-заявки на перевозку",
            raw_response: { pdf_size_bytes: 10240 },
          },
          user_input_json: {
            kind: "transport_order_pdf",
            customer_name: "ООО Тест",
            loading_address: "Москва",
            unloading_address: "Казань",
            cargo_name: "Товар",
          },
        }}
      />
    );
    expect(screen.getByTestId("pdf-stored-kb")).toHaveTextContent("10.0");
    expect(screen.getByText(/PDF заявки \(из лога вызова\)/)).toBeInTheDocument();
  });

  it("compose: requests PDF when showing preview", async () => {
    render(
      <TransportOrderPdfPanel
        call={{
          endpoint: "transport_order_compose",
          raw_data_json: {
            raw_response: {
              fields: {
                customer_name: "ООО",
                loading_address: "Москва",
                unloading_address: "Казань",
                cargo_name: "груз",
              },
            },
            presentation: {
              pdf_attachment_hint: { page_count_typical: 1 },
            },
          },
        }}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /Показать PDF/ }));
    await waitFor(() => {
      expect(client.api.transportOrderPdf).toHaveBeenCalled();
    });
    const spy = client.api.transportOrderPdf as unknown as ReturnType<typeof vi.fn>;
    const arg = spy.mock.calls[0][0] as Record<string, unknown>;
    expect(arg.pdf_engine).toBe("fpdf");
    expect(arg.customer_name).toBe("ООО");
  });

  it("renders nothing for unrelated endpoint", () => {
    const { container } = render(<TransportOrderPdfPanel call={{ endpoint: "query" }} />);
    expect(container.firstChild).toBeNull();
  });
});
