import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { arena, session } from "../../test/fixtures";
import { formatDuration, RevealCard } from "./RevealCard";

const card = {
  retained_seconds: 252,
  post_diversion_steps: 9,
  post_diversion_attempts: 3,
  honeytools_touched: ["get_service_credentials", "export_customer_records"],
  credential_issued: true,
  token_reused: true,
};

function mockApi(revealed: boolean, reveal: () => Response) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path === "/api/arena/state") return Response.json({ ...arena, revealed });
    if (path === "/api/decoy/reveal") return reveal();
    throw new Error(`Unexpected request ${path}`);
  });
}

afterEach(() => vi.restoreAllMocks());

describe("RevealCard", () => {
  it("formatea la duración", () => {
    expect(formatDuration(45)).toBe("45 s");
    expect(formatDuration(252)).toBe("4 min 12 s");
  });

  it("no muestra nada ni consulta la tarjeta antes de la revelación", async () => {
    const mock = mockApi(false, () => Response.json(card));
    const { container } = render(<RevealCard session={session} />);
    await vi.waitFor(() =>
      expect(mock).toHaveBeenCalledWith("/api/arena/state", expect.anything()),
    );
    expect(container).toBeEmptyDOMElement();
    expect(mock.mock.calls.some(([path]) => String(path) === "/api/decoy/reveal")).toBe(false);
  });

  it("tras la revelación muestra los números de la sesión desviada", async () => {
    const mock = mockApi(true, () => Response.json(card));
    render(<RevealCard session={session} />);
    expect(await screen.findByRole("heading", { name: "Eso era un señuelo" })).toBeInTheDocument();
    expect(screen.getByText(/Te retuvo 4 min 12 s/)).toBeInTheDocument();
    expect(screen.getByText(/9 pasos de herramientas en 3 intentos/)).toBeInTheDocument();
    expect(screen.getByText(/Cebos tocados: 2/)).toBeInTheDocument();
    expect(
      screen.getByText(/credencial que nunca existió y la volviste a usar/),
    ).toBeInTheDocument();
    const call = mock.mock.calls.find(([path]) => String(path) === "/api/decoy/reveal");
    expect(call?.[1]?.headers).toEqual({ Authorization: "Bearer signed-token" });
  });

  it("no muestra la tarjeta si la sesión no pasó por el señuelo", async () => {
    mockApi(true, () =>
      Response.json({ detail: "Tu sesión no pasó por el señuelo." }, { status: 404 }),
    );
    const { container } = render(<RevealCard session={session} />);
    await vi.waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(2));
    expect(container).toBeEmptyDOMElement();
  });
});
