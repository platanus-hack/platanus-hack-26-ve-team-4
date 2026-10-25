import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Policy } from "../operator/api";
import { PolicyStory } from "./PolicyStory";

const policies: Policy[] = [
  { version: 0, status: "superseded", rules: [], reason: "Base", validation: {} },
  {
    version: 1,
    parent_version: 0,
    status: "active",
    rules: ["memory_key_allowlist"],
    reason: "La memoria solo conserva preferencias.",
    validation: {
      cases: [
        { name: "original", passed: true, adversarial: true },
        { name: "preference", passed: true, adversarial: false },
      ],
    },
  },
];

describe("PolicyStory", () => {
  it("explica qué es una política y cuenta cada versión", () => {
    render(<PolicyStory policies={policies} attempts={[]} />);
    expect(screen.getByText(/Una política es la lista de reglas/)).toBeInTheDocument();
    expect(screen.getByText("Punto de partida")).toBeInTheDocument();
    expect(screen.getByText(/guardar en memoria un permiso falso/)).toBeInTheDocument();
    expect(screen.getByText(/Bloqueó 1\/1 repeticiones del ataque/)).toBeInTheDocument();
    expect(screen.getByText("1 versión nueva en esta ronda.")).toBeInTheDocument();
  });

  it("dice que no hay versiones nuevas si ningún ataque logró nada", () => {
    render(<PolicyStory policies={policies.slice(0, 1)} attempts={[]} />);
    expect(screen.getByText(/Todavía no hay versiones nuevas/)).toBeInTheDocument();
  });
});
