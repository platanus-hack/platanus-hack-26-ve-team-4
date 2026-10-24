import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { GuardPolicyCard } from "./GuardPolicyCard";
import { active, proposed, superseded } from "./guardFixtures";

describe("GuardPolicyCard", () => {
  it("muestra versión, padre, estado, reglas legibles e informe", () => {
    render(
      <GuardPolicyCard policy={active} disabled={false} activate={vi.fn()} rollback={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { name: /Versión 2 · activa/ })).toBeInTheDocument();
    expect(screen.getByText(/Padre: versión 1/)).toBeInTheDocument();
    expect(screen.getByText("DENEGAR transferir SI monto > 500")).toBeInTheDocument();
    expect(screen.getByText("Tareas legítimas conservadas: 4/4")).toBeInTheDocument();
  });

  it("permite activar una propuesta y no revertirla", async () => {
    const activate = vi.fn();
    render(
      <GuardPolicyCard policy={proposed} disabled={false} activate={activate} rollback={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: /Revertir/ })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Activar versión 3" }));
    expect(activate).toHaveBeenCalledWith(3);
  });

  it("permite revertir la activa y no ofrece acciones en las reemplazadas", async () => {
    const rollback = vi.fn();
    const { rerender } = render(
      <GuardPolicyCard policy={active} disabled={false} activate={vi.fn()} rollback={rollback} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Revertir versión 2" }));
    expect(rollback).toHaveBeenCalledWith(2);
    rerender(
      <GuardPolicyCard
        policy={superseded}
        disabled={false}
        activate={vi.fn()}
        rollback={rollback}
      />,
    );
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("deshabilita los botones mientras hay una operación", () => {
    render(<GuardPolicyCard policy={proposed} disabled activate={vi.fn()} rollback={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Activar versión 3" })).toBeDisabled();
  });
});
