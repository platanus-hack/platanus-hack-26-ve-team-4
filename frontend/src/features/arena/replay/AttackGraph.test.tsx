import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AttackGraph, wrap } from "./AttackGraph";
import { replay } from "./replayFixtures";

describe("AttackGraph", () => {
  it("dibuja el efecto indebido con texto además de color", () => {
    const { container } = render(
      <AttackGraph graph={replay.before.graph} version={1} cut={false} />,
    );
    expect(screen.getByRole("img", { name: /llega al efecto indebido/ })).toBeInTheDocument();
    expect(screen.getByText("efecto indebido")).toBeInTheDocument();
    expect(screen.getByText("get_order")).toBeInTheDocument();
    expect(screen.queryByText("bloqueado")).not.toBeInTheDocument();
    expect(container.querySelector(".replay-edge--effect")).not.toBeNull();
  });

  it("corta la arista y rotula bloqueado solo cuando se ordena", () => {
    const { container, rerender } = render(
      <AttackGraph graph={replay.after.graph} version={2} cut={false} />,
    );
    expect(screen.queryByText("bloqueado")).not.toBeInTheDocument();
    expect(container.querySelector(".replay-edge--blocked")).toBeNull();
    rerender(<AttackGraph graph={replay.after.graph} version={2} cut />);
    expect(screen.getByText("bloqueado")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /queda bloqueado antes del efecto/ })).toBeVisible();
    expect(container.querySelector(".replay-edge--blocked")).not.toBeNull();
  });

  it("muestra una fila por llamada y parte los nombres largos", () => {
    const graph = {
      nodes: [
        { id: "agent", kind: "agent" as const, label: "Agente de soporte" },
        { id: "tool-0", kind: "tool" as const, label: "search_knowledge", state: "ok" as const },
        { id: "tool-1", kind: "tool" as const, label: "save_memory", state: "ok" as const },
      ],
      edges: [
        { from: "agent", to: "tool-0", state: "ok" as const },
        { from: "agent", to: "tool-1", state: "ok" as const },
      ],
    };
    const { container } = render(<AttackGraph graph={graph} version={0} cut={false} />);
    expect(container.querySelector("svg")?.getAttribute("viewBox")).toBe("0 0 360 128");
    expect(wrap("search_knowledge", 8)).toEqual(["search_", "knowledge"]);
  });
});
