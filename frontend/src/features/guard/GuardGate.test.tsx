import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GuardGate } from "./GuardGate";
import { active } from "./guardFixtures";

describe("GuardGate", () => {
  it("muestra los tres totales de la compuerta", () => {
    render(<GuardGate gate={active.report.gate} />);
    expect(screen.getByText("Compuerta aprobada")).toBeInTheDocument();
    expect(screen.getByText("Llamadas violatorias bloqueadas: 1/1")).toBeInTheDocument();
    expect(screen.getByText("Tareas legítimas conservadas: 4/4")).toBeInTheDocument();
    expect(screen.getByText("Inyecciones simuladas bloqueadas: 0/0")).toBeInTheDocument();
  });

  it("indica la compuerta rechazada y la ausencia de informe", () => {
    const { rerender } = render(
      <GuardGate gate={active.report.gate && { ...active.report.gate, accepted: false }} />,
    );
    expect(screen.getByText("Compuerta rechazada")).toBeInTheDocument();
    rerender(<GuardGate />);
    expect(screen.getByText("Sin informe de compuerta.")).toBeInTheDocument();
  });
});
