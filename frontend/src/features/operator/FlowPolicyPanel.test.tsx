import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Policy } from "./api";
import { FlowPolicyPanel } from "./FlowPolicyPanel";

const synthesized: Policy = {
  version: 1,
  status: "active",
  rules: [],
  reason: "Reglas de flujo.",
  validation: {
    passed: true,
    integrity_probe: { passed: true, outcome: "prevented", untrusted_effects: 0 },
  },
  flow_rules: [
    {
      rule_id: "request_refund_amount_untrusted",
      tool: "request_refund",
      reason: "El argumento amount proviene de contenido no confiable.",
      text: "DENEGAR request_refund SI amount viene de una fuente no confiable",
      deny_when: { kind: "untrusted_origin", argument: "amount" },
    },
  ],
  synthesis: {
    status: "accepted",
    source: "synthesized",
    llm_mode: "demo",
    precheck: {
      accepted: true,
      reason: "ok",
      original_blocked: 1,
      original_total: 1,
      legitimate_kept: 3,
      legitimate_total: 3,
    },
    trace: [{ tool: "request_refund", provenance: { amount: "untrusted", order_id: "user" } }],
  },
};

describe("FlowPolicyPanel", () => {
  it("muestra las reglas, la procedencia, la compuerta y la sonda", () => {
    render(<FlowPolicyPanel policy={synthesized} />);
    expect(screen.getByText("Política de flujo sintetizada desde el hallazgo")).toBeTruthy();
    expect(screen.getByText(/DENEGAR request_refund SI amount/)).toBeTruthy();
    expect(screen.getByText(/integridad baja/)).toBeTruthy();
    expect(screen.getByText(/bloquea 1\/1/)).toBeTruthy();
    expect(screen.getByText(/ningún efecto con argumentos no confiables/)).toBeTruthy();
    expect(screen.getByText(/Modo demo/)).toBeTruthy();
  });

  it("explica el rechazo de la síntesis y el efecto que la tabla dejó pasar", () => {
    render(
      <FlowPolicyPanel
        policy={{
          version: 1,
          status: "active",
          rules: ["refund_within_limit"],
          reason: "Catálogo.",
          validation: {
            integrity_probe: { passed: true, outcome: "not_achieved", untrusted_effects: 1 },
            synthesis: {
              status: "rejected",
              precheck: {
                accepted: false,
                reason: "La política bloquearía llamadas legítimas: valid-refund.",
                original_blocked: 1,
                original_total: 1,
                legitimate_kept: 2,
                legitimate_total: 3,
              },
            },
          },
        }}
      />,
    );
    expect(screen.getByText(/Síntesis rechazada/)).toBeTruthy();
    expect(screen.getByText(/1 efecto\(s\) ejecutado\(s\)/)).toBeTruthy();
  });
});
