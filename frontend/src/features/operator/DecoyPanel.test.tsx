import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { arena } from "../../test/fixtures";
import type { DecoyCase, DecoySummary } from "./api";
import { DecoyPanel } from "./DecoyPanel";

function made(alias: string, overrides: Partial<DecoyCase> = {}): DecoyCase {
  return {
    session_id: `sess-${alias}`,
    alias,
    reason: "confirmed_violation",
    retained_seconds: 252,
    post_diversion_steps: 9,
    post_diversion_attempts: 3,
    honeytools_touched: ["get_service_credentials"],
    credential_issued: true,
    token_reused: true,
    retained: true,
    bait_taken: true,
    deceived: true,
    ...overrides,
  };
}
function summary(overrides: Partial<DecoySummary> = {}): DecoySummary {
  return {
    diverted_n: 0,
    excluded_autonomous_n: 0,
    small_n: true,
    retained: { k: 0, n: 0, value: null },
    bait_taken: { k: 0, n: 0, value: null },
    deceived: { k: 0, n: 0, value: null },
    median_retained_seconds: null,
    cases: [],
    ...overrides,
  };
}
function mockApi(body: DecoySummary) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path === "/api/arena/state") return Response.json(arena);
    if (path === "/api/operator/decoy") return Response.json(body);
    throw new Error(`Unexpected request ${path}`);
  });
}

afterEach(() => vi.restoreAllMocks());

describe("DecoyPanel", () => {
  it("dice n = 0 cuando nadie pasó al señuelo", async () => {
    const mock = mockApi(summary());
    render(<DecoyPanel secret="operator-secret-123" />);
    expect(await screen.findByText(/ninguna sesión de la audiencia/)).toBeInTheDocument();
    const call = mock.mock.calls.find(([path]) => String(path) === "/api/operator/decoy");
    expect(call?.[1]?.headers).toEqual(
      expect.objectContaining({ "X-Operator-Secret": "operator-secret-123" }),
    );
  });

  it("con n pequeño muestra los casos y ningún porcentaje", async () => {
    mockApi(
      summary({
        diverted_n: 2,
        excluded_autonomous_n: 1,
        cases: [made("neo"), made("trinity", { token_reused: false })],
      }),
    );
    render(<DecoyPanel secret="s" />);
    expect(await screen.findByText(/n = 2 sesiones desviadas/)).toBeInTheDocument();
    expect(screen.getByText(/1 del Prober excluidas/)).toBeInTheDocument();
    expect(screen.getByText(/no se publican porcentajes/)).toBeInTheDocument();
    expect(screen.getByText("neo")).toBeInTheDocument();
    expect(screen.getByText("trinity")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("%");
  });

  it("con n suficiente muestra k/n y el rótulo de origen", async () => {
    mockApi(
      summary({
        diverted_n: 6,
        small_n: false,
        retained: { k: 5, n: 6, value: 0.8333 },
        bait_taken: { k: 3, n: 6, value: 0.5 },
        deceived: { k: 2, n: 6, value: 0.3333 },
        median_retained_seconds: 90,
        cases: [made("neo")],
      }),
    );
    render(<DecoyPanel secret="s" />);
    expect(await screen.findByText(/Retenidas: 5\/6 · 83 %/)).toBeInTheDocument();
    expect(
      screen.getByText(/Engañadas \(credencial reutilizada\): 2\/6 · 33 %/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Retención mediana: 1 min 30 s/)).toBeInTheDocument();
    expect(screen.getByText(/Demostración simulada/)).toBeInTheDocument();
  });
});
