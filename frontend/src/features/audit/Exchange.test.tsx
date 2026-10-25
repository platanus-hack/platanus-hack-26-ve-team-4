import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Exchange } from "./Exchange";
import type { AuditAttempt } from "./types";

const base: AuditAttempt = {
  id: "att-1",
  position: 1,
  created_at: "2026-10-25T10:02:00Z",
  updated_at: "2026-10-25T10:02:01Z",
  duration_seconds: 1,
  status: "evaluated",
  outcome: "prevented",
  route: "protected",
  policy_version: 0,
  origin: "audience",
  objective_id: null,
  campaign_id: null,
  messages: ["Hola"],
  reply: "Buenas",
  verdicts: [],
  detail: "",
  family: "tool_misuse",
  tools: [
    {
      event_id: 3,
      kind: "tool_denied",
      tool: "get_order",
      arguments: { order_id: "B-2001" },
      provenance: { order_id: "user" },
      validator: "order_owner",
      effect: {},
      output: {},
      reason: "input_blocked",
      stage: "input_armor",
    },
  ],
};

function renderExchange(attempt: AuditAttempt, live?: boolean) {
  return render(
    <ol>
      <Exchange attempt={attempt} live={live} />
    </ol>,
  );
}

describe("Exchange", () => {
  it("sin modo en vivo no muestra la clasificación y deja la traza cerrada", () => {
    const { container } = renderExchange(base);
    expect(screen.queryByText("Clasificación")).not.toBeInTheDocument();
    expect(screen.queryByText(/Familia:/)).not.toBeInTheDocument();
    expect(screen.queryByText("Negado por order_owner")).not.toBeInTheDocument();
    expect(container.querySelector("details")).not.toHaveAttribute("open");
    // El motivo de Armor sigue visible dentro de la traza del paso denegado.
    expect(screen.getByText(/Armor bloqueó los argumentos de entrada/)).toBeInTheDocument();
  });

  it("en modo en vivo muestra estado, familia, ruta, negaciones y el motivo de Armor con la traza abierta", () => {
    const { container } = renderExchange(base, true);
    expect(screen.getByLabelText("Clasificación")).toBeInTheDocument();
    expect(screen.getByText("Familia: Uso indebido de herramientas")).toBeInTheDocument();
    expect(screen.getByText("Evaluado")).toBeInTheDocument();
    expect(screen.getByText("Ruta: protegida")).toBeInTheDocument();
    expect(screen.getByText("Negado por order_owner")).toBeInTheDocument();
    expect(screen.getByText(/Armor bloqueó los argumentos de entrada/)).toBeInTheDocument();
    expect(container.querySelector("details")).toHaveAttribute("open");
  });

  it("muestra el estado en cola y la espera cuando aún no hay respuesta", () => {
    renderExchange({ ...base, status: "queued", reply: "", tools: [], family: null }, true);
    expect(screen.getByText("En cola")).toBeInTheDocument();
    expect(screen.getByText("Familia: —")).toBeInTheDocument();
    expect(screen.getByText("Esperando respuesta…")).toBeInTheDocument();
    expect(screen.queryByText(/Sin respuesta/)).not.toBeInTheDocument();
  });
});
