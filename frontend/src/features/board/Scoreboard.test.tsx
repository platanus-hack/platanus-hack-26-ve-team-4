import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { arena } from "../../test/fixtures";
import type { ArenaState } from "../arena/types";
import { Scoreboard } from "./Scoreboard";

const provisional: ArenaState = {
  ...arena,
  revealed: false,
  provisional: true,
  confirmed_violations: 1,
  contained_honeypot: 2,
  scores: [{ alias: "neo", score: 2 }],
};

describe("Scoreboard", () => {
  it("antes de revelar muestra el marcador provisional con los aparentes y los contadores en vivo", () => {
    render(<Scoreboard arena={provisional} />);
    const panel = screen.getByLabelText("Marcador");

    expect(within(panel).getByText("Marcador provisional")).toBeInTheDocument();
    expect(within(panel).getByText("provisional")).toBeInTheDocument();
    expect(within(panel).getByText("provisional")).toHaveAttribute(
      "title",
      "Puntos aparentes: incluyen intentos contenidos en el señuelo",
    );
    expect(within(panel).getByText("neo")).toBeInTheDocument();
    expect(within(panel).getByText("2 puntos")).toBeInTheDocument();
    expect(within(panel).getByText("Confirmadas").nextSibling).toHaveTextContent("1");
    expect(within(panel).getByText("En el señuelo").nextSibling).toHaveTextContent("2");
    expect(within(panel).queryByText(/aparentes ·/)).not.toBeInTheDocument();
    expect(panel.textContent).not.toMatch(/oculto|pendiente de revelación/i);
  });

  it("tras revelar muestra el marcador final con la reconciliación por fila", () => {
    render(
      <Scoreboard
        arena={{
          ...arena,
          revealed: true,
          provisional: false,
          confirmed_violations: 1,
          contained_honeypot: 1,
          scores: [{ alias: "neo", score: 1, apparent: 2, contained: 1 }],
        }}
      />,
    );
    const panel = screen.getByLabelText("Marcador");

    expect(within(panel).getByText("Marcador final")).toBeInTheDocument();
    expect(within(panel).queryByText("provisional")).not.toBeInTheDocument();
    expect(
      within(panel).getByText("2 aparentes · 1 confirmados · 1 en el señuelo"),
    ).toBeInTheDocument();
    expect(within(panel).getByText("1 punto")).toBeInTheDocument();
  });

  it("sin puntos dice que aún no hay objetivos logrados", () => {
    render(<Scoreboard arena={{ ...provisional, scores: [] }} />);
    expect(screen.getByText("Aún no hay objetivos logrados.")).toBeInTheDocument();
  });

  it("sin estado de la ronda dice que el marcador no está disponible", () => {
    render(<Scoreboard arena={null} />);
    expect(screen.getByText("Marcador no disponible")).toBeInTheDocument();
  });
});
