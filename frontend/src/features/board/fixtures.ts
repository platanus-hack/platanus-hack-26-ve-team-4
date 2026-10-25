// Datos de prueba de la Arena en vivo con la forma de GET /api/operator/live v2.
import type { LiveAttempt, LiveBoard, LiveKpis, LiveSession } from "./types";

export const NOW = "2026-10-24T15:01:00+00:00";

export function liveAttempt(overrides: Partial<LiveAttempt> = {}): LiveAttempt {
  return {
    id: "att-1",
    number: 1,
    status: "evaluated",
    outcome: "not_achieved",
    route: "protected",
    policy_version: 0,
    messages: ["Consulta mi pedido."],
    reply: "Aquí tienes tu pedido.",
    denials: [],
    violated_objectives: [],
    patched_by: null,
    technique: null,
    created_at: "2026-10-24T15:00:00+00:00",
    updated_at: "2026-10-24T15:00:00+00:00",
    ...overrides,
  };
}

export function liveSession(id: string, overrides: Partial<LiveSession> = {}): LiveSession {
  const attempts = overrides.attempts ?? [liveAttempt({ id: `att-${id}` })];
  return {
    session_id: id,
    alias: `Agente-${id}`,
    kind: "swarm",
    concealed: false,
    route: "protected",
    customer_id: "cust-1",
    last_activity: `2026-10-24T15:00:${id.padStart(2, "0").slice(-2)}+00:00`,
    attempt_total: attempts.length,
    contained_n: 0,
    prevented_n: 0,
    leaked_n: 0,
    ...overrides,
    attempts,
  };
}

/** Sesión del Público antes de revelar, tal como la manda el servidor (sin resultado ni respuesta). */
export function concealedSession(id: string, overrides: Partial<LiveSession> = {}): LiveSession {
  return liveSession(id, {
    alias: `Visitante-${id}`,
    kind: "audience",
    concealed: true,
    route: null,
    contained_n: null,
    prevented_n: null,
    leaked_n: null,
    attempts: [liveAttempt({ id: `att-${id}`, outcome: null, route: null, reply: "" })],
    ...overrides,
  });
}

export const kpis: LiveKpis = {
  attacks: { n: 72, audience: 0, swarm: 60, prober: 12, in_flight: 2, source: "x" },
  safe_space: {
    n: 15,
    safe_sessions: 6,
    diverted_sessions: 7,
    contained_attempts: 53,
    scope: "swarm_prober",
    label: "Solo enjambre y Prober hasta revelar",
    source: "x",
  },
  leaked: {
    n: 66,
    leaked: 7,
    by_objective: { "OBJ-ORDER": 6, "OBJ-MEMORY": 3, "OBJ-REFUND": 1 },
    objective_sum: 10,
    scope: "swarm_prober",
    label: "Solo enjambre y Prober hasta revelar",
    source: "x",
  },
  attacker_tokens: {
    measured: false,
    label: "no medido en modo demo",
    attacker: { measured: false, tokens: null, calls: 0 },
    decoy: { measured: false, tokens: null, calls: 0 },
    n: 0,
    source: "x",
  },
  patches: {
    n: 2,
    activated: 2,
    current_version: 2,
    median_seconds_to_patch: 6,
    findings_covered: 2,
    findings_total: 3,
    source: "x",
  },
};

export function board(sessions: LiveSession[], overrides: Partial<LiveBoard> = {}): LiveBoard {
  return {
    revealed: false,
    accepting: true,
    llm_mode: "demo",
    policy_version: 2,
    sessions_total: 18,
    sessions,
    kpis,
    generated_at: NOW,
    ...overrides,
  };
}
