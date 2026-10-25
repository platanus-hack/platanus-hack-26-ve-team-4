import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { kpis } from "./fixtures";
import { KpiColumn } from "./KpiColumn";
import type { LiveKpis } from "./types";

describe("KpiColumn", () => {
  it("dibuja 5 tiles con las cifras y las bases que da el servidor", () => {
    render(<KpiColumn kpis={kpis} sessionsTotal={18} />);
    const column = screen.getByLabelText("Analíticas");
    expect(column.querySelectorAll(".av-tile")).toHaveLength(5);

    const attacks = screen.getByLabelText("Interacciones");
    expect(
      within(attacks).getByText("n = 72 interacciones · 18 sesiones · 2 en curso"),
    ).toBeVisible();
    expect(within(attacks).getByText("Agentes simulados").nextSibling).toHaveTextContent("60");

    const safe = screen.getByLabelText("Espacio seguro");
    expect(safe.querySelector(".av-k-num")).toHaveTextContent("6/15");
    expect(within(safe).getByText("40 %")).toBeInTheDocument();
    expect(within(safe).getByText(/sin Público/)).toBeInTheDocument();

    const leaked = screen.getByLabelText("Ataques que dejamos pasar");
    expect(leaked.querySelector(".av-k-num")).toHaveTextContent("7");
    expect(within(leaked).getByText("de 66 sin Público · Σ 10 obj. (se solapan)")).toBeVisible();

    const patches = screen.getByLabelText("Parches que aprendió la defensa");
    expect(within(patches).getByText("v2")).toBeInTheDocument();
    expect(within(patches).getByText("6 s")).toBeInTheDocument();
    expect(within(patches).getByText("n = 3 hallazgos · 2 cubiertos · mediana")).toBeVisible();
  });

  it("no inventa un cero cuando los tokens no se midieron", () => {
    render(<KpiColumn kpis={kpis} sessionsTotal={18} />);
    const tokens = screen.getByLabelText("Tokens: atacante y señuelo");

    expect(within(tokens).getByText("No medido")).toBeInTheDocument();
    expect(within(tokens).getByText("no medido en modo demo")).toBeInTheDocument();
    expect(within(tokens).getByText("(modo demo)")).toBeInTheDocument();
    expect(tokens.querySelector(".av-k-num")).toHaveTextContent("—");
    expect(within(tokens).queryByText("0")).not.toBeInTheDocument();
  });

  it("muestra los tokens medidos en miles cuando el ledger los tiene", () => {
    const measured: LiveKpis = {
      ...kpis,
      leaked: { ...kpis.leaked, scope: "all", label: "Toda la ronda" },
      attacker_tokens: {
        measured: true,
        label: "",
        attacker: { measured: true, tokens: 54070, calls: 31 },
        decoy: { measured: false, tokens: null, calls: 0 },
        n: 31,
        source: "x",
      },
    };
    render(<KpiColumn kpis={measured} sessionsTotal={18} />);
    const tokens = screen.getByLabelText("Tokens: atacante y señuelo");

    expect(tokens.querySelector(".av-k-num")).toHaveTextContent("54,1k");
    expect(within(tokens).getByText("Señuelo").nextSibling).toHaveTextContent("no medido");
    expect(screen.getByText("de 66 · Σ 10 obj. (se solapan)")).toBeInTheDocument();
  });

  it("sin hallazgos ni sesiones con alcance no muestra porcentajes ni medianas inventadas", () => {
    const empty: LiveKpis = {
      ...kpis,
      safe_space: { ...kpis.safe_space, n: 0, safe_sessions: 0 },
      patches: { ...kpis.patches, median_seconds_to_patch: null },
    };
    render(<KpiColumn kpis={empty} sessionsTotal={0} />);

    expect(within(screen.getByLabelText("Espacio seguro")).getByText("—")).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Parches que aprendió la defensa")).getByText("—"),
    ).toBeInTheDocument();
  });
});
