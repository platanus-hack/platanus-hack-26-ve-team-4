import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CoevolutionChart } from "./CoevolutionChart";
import type { CoevolutionResponse, CoevolutionRound } from "./types";

function round(overrides: Partial<CoevolutionRound>): CoevolutionRound {
  return {
    version: 0,
    queries: 8,
    evaluable: 8,
    inconclusive: 0,
    pending: 0,
    violations: 0,
    success_rate: 0,
    ci_low: 0,
    ci_high: 0.32,
    queries_to_break: null,
    censored: true,
    first_break: null,
    ...overrides,
  };
}

function respond(body: unknown) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(body));
}

afterEach(() => vi.restoreAllMocks());

describe("curva de co-evolución", () => {
  it("muestra el estado vacío y la salvedad sin campaña", async () => {
    respond({ budget: 8, evidence_mode: "simulated", status: null, versions: [], summary: null });
    render(<CoevolutionChart />);
    expect(await screen.findByText(/Sin campaña adaptativa/)).toBeInTheDocument();
    expect(screen.getByText(/no general/)).toBeInTheDocument();
  });

  it("muestra n por punto, el contador censurado y no rompe con otra respuesta", async () => {
    const broken = round({
      version: 0,
      queries: 3,
      evaluable: 3,
      violations: 1,
      success_rate: 1 / 3,
      ci_low: 0.06,
      ci_high: 0.79,
      queries_to_break: 3,
      censored: false,
      first_break: { mutator: "chain", family: "direct_injection" },
    });
    const held = round({ version: 1 });
    const body: CoevolutionResponse = {
      budget: 8,
      evidence_mode: "simulated",
      status: "exhausted",
      versions: [broken, held],
      summary: { baseline: broken, latest: held },
    };
    respond(body);
    render(<CoevolutionChart />);
    expect(await screen.findByText("n=3")).toBeInTheDocument();
    expect(screen.getByText("n=8")).toBeInTheDocument();
    expect(screen.getByText(/se rompió en la consulta 3/)).toBeInTheDocument();
    expect(screen.getByText(/≥ 8 consultas sin romper/)).toBeInTheDocument();
    expect(screen.getByText(/Evidencia simulada/)).toBeInTheDocument();
  });

  it("ignora una respuesta sin versiones", async () => {
    respond({ accepting: true });
    render(<CoevolutionChart />);
    expect(await screen.findByText(/Sin campaña adaptativa/)).toBeInTheDocument();
  });
});
