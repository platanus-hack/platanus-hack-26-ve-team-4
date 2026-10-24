import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GuardFindings } from "./GuardFindings";
import { findings } from "./guardFixtures";

describe("GuardFindings", () => {
  it("muestra invariantes rotos, versión y resuelto por", () => {
    render(<GuardFindings findings={findings} />);
    expect(
      screen.getByText("tope-por-transferencia, beneficiarios-registrados"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Detectado con la versión 0 · resuelto por la versión 1/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Detectado con la versión 1 · sin resolver/)).toBeInTheDocument();
  });

  it("indica cuando no hay hallazgos", () => {
    render(<GuardFindings findings={[]} />);
    expect(screen.getByText("Sin invariantes rotos.")).toBeInTheDocument();
  });
});
