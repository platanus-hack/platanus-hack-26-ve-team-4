import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GuardPolicies } from "./GuardPolicies";
import { active, superseded } from "./guardFixtures";

describe("GuardPolicies", () => {
  it("lista todas las versiones", () => {
    render(
      <GuardPolicies
        policies={[superseded, active]}
        disabled={false}
        activate={vi.fn()}
        rollback={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: "Versiones de política · 2" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Versión 1 · reemplazada/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Versión 2 · activa/ })).toBeInTheDocument();
  });

  it("explica la ausencia de versiones", () => {
    render(<GuardPolicies policies={[]} disabled={false} activate={vi.fn()} rollback={vi.fn()} />);
    expect(
      screen.getByText("Este contrato aún no tiene versiones de política."),
    ).toBeInTheDocument();
  });
});
