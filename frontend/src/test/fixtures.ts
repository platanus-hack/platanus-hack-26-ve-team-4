import type { ArenaState } from "../features/arena/types";
import type { ArenaSession, Attempt } from "../features/participant/types";

export const session: ArenaSession = {
  id: "sess-1",
  alias: "neo",
  token: "signed-token",
  created_at: "2026-10-24T00:00:00Z",
  expires_at: "2099-10-24T01:00:00Z",
  customer_name: "Ana",
  order_ids: ["A-1001", "A-1002"],
  objectives: ["OBJ-ORDER", "OBJ-REFUND", "OBJ-MEMORY"],
  attempts_per_minute: 12,
};
export const arena: ArenaState = {
  accepting: true,
  provisional: true,
  revealed: false,
  policy_version: 0,
  attempts: 0,
  scores: [],
  round_id: "round-1",
  started_at: "2026-10-24T00:00:00Z",
  session_count: 1,
  session_limit: 100,
  llm_mode: "demo",
  evidence_mode: "simulated",
};
export function attempt(overrides: Partial<Attempt> = {}): Attempt {
  return {
    id: "attempt-1",
    status: "evaluated",
    outcome: "prevented",
    reply: "Solicitud rechazada.",
    policy_version: 1,
    created_at: "2026-10-24T01:00:00Z",
    messages: ["Consulta B-2001"],
    ...overrides,
  };
}
export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}
