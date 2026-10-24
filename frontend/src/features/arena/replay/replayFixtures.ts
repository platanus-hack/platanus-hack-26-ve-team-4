import type { TraceEvent } from "../types";
import type { Replay } from "./types";

export const replay: Replay = {
  version: 2,
  source: "repetición de las llamadas a herramientas registradas",
  before: {
    version: 1,
    graph: {
      nodes: [
        { id: "agent", kind: "agent", label: "Agente de soporte" },
        { id: "tool-0", kind: "tool", label: "get_order", state: "ok" },
        {
          id: "effect-0",
          kind: "effect",
          label: "Pedido ajeno leído",
          effect: "foreign_order_read",
          state: "effect",
        },
      ],
      edges: [
        { from: "agent", to: "tool-0", state: "ok" },
        { from: "tool-0", to: "effect-0", state: "effect" },
      ],
    },
  },
  after: {
    version: 2,
    graph: {
      nodes: [
        { id: "agent", kind: "agent", label: "Agente de soporte" },
        { id: "tool-0", kind: "tool", label: "get_order", state: "ok" },
        {
          id: "effect-0",
          kind: "effect",
          label: "Pedido ajeno leído",
          effect: "foreign_order_read",
          state: "prevented",
        },
      ],
      edges: [
        { from: "agent", to: "tool-0", state: "ok" },
        {
          from: "tool-0",
          to: "effect-0",
          state: "blocked",
          control: "order_belongs_to_session_customer",
        },
      ],
    },
  },
  legit: [
    { name: "own-order", passed: true, tool: "get_order" },
    { name: "valid-refund", passed: true, tool: "request_refund" },
  ],
};

export function validated(version: number, passed = true): TraceEvent {
  return {
    id: version,
    type: "patch_validated",
    visibility: "public",
    attempt_id: null,
    session_id: null,
    policy_version: version,
    timestamp: "2026-10-24T00:00:00Z",
    data: { version, passed },
  };
}
