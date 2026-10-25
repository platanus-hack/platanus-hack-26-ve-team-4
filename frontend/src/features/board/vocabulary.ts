// Vocabulario de la Arena en vivo: códigos del servidor a texto legible (maqueta aprobada).
import type { LiveAttempt, LiveDenial, LiveTechnique, RouteName, SessionKind } from "./types";

export type Segment = "leak" | "blocked" | "safe" | "neutral";

interface OutcomeView {
  cls: string;
  seg: Segment;
  text: (attempt: LiveAttempt) => string;
}

const objective = (attempt: LiveAttempt) =>
  attempt.violated_objectives.length ? ` · ${attempt.violated_objectives.join(", ")}` : "";

// La palabra "señuelo" solo aparece en la insignia de ruta; los chips no la repiten.
export const OUTCOME: Record<string, OutcomeView> = {
  confirmed_violation: { cls: "o-leak", seg: "leak", text: (a) => `Se filtró${objective(a)}` },
  prevented: {
    cls: "o-blocked",
    seg: "blocked",
    text: (a) => `Bloqueado${a.policy_version > 0 ? ` · parche v${a.policy_version}` : ""}`,
  },
  contained_honeypot: { cls: "o-safe", seg: "safe", text: () => "Contenido" },
  not_achieved: { cls: "o-neutral", seg: "neutral", text: () => "No logrado" },
  inconclusive: { cls: "o-incon", seg: "neutral", text: () => "Inconcluso" },
};
/** Cualquier desenlace desconocido se muestra como inconcluso: nunca se inventa un color. */
export const UNKNOWN_OUTCOME: OutcomeView = {
  cls: "o-incon",
  seg: "neutral",
  text: () => "Sin clasificar",
};

export function outcomeView(attempt: LiveAttempt): OutcomeView {
  const key = attempt.outcome ?? (attempt.status === "inconclusive" ? "inconclusive" : "");
  return OUTCOME[key] ?? UNKNOWN_OUTCOME;
}

/** Motivos de `GatewayReason` y validadores frecuentes. */
export const DENIAL: Record<string, string> = {
  business_rule_denied: "regla de negocio",
  rate_limited: "límite de uso",
  tool_not_in_manifest: "fuera del manifiesto",
  input_blocked: "entrada bloqueada",
  output_blocked: "salida bloqueada",
  tool_unregistered: "herramienta no registrada",
  region_not_allowed_by_policy: "región no permitida",
  order_belongs_to_session_customer: "pedido ajeno",
  refund_within_limit: "límite de reembolso",
  memory_key_allowlist: "memoria protegida",
  require_provenance: "origen sin verificar",
};

export function denialLabel(denial: LiveDenial): string {
  if (denial.validator) {
    const known = DENIAL[denial.validator];
    if (known) return known;
    if (denial.validator.startsWith("flow:")) return "regla de flujo";
  }
  return DENIAL[denial.reason] ?? (denial.reason.replaceAll("_", " ") || "control del gateway");
}

/** Valores de `AttackFamily`. */
export const FAMILY: Record<string, string> = {
  direct_injection: "inyección directa",
  indirect_injection: "inyección indirecta",
  goal_hijacking: "secuestro de objetivo",
  tool_misuse: "abuso de herramienta",
  tool_poisoning: "herramienta envenenada",
  memory_poisoning: "envenenar memoria",
};
export const MUTATOR: Record<string, string> = {
  paraphrase_es: "paráfrasis",
  paraphrase_en: "en inglés",
  split_turns: "en varios turnos",
  channel_document: "por documento",
  channel_tool_result: "por herramienta",
  chain: "encadenado",
};

/** Etiqueta de técnica; null si no se conoce (no se pinta nada). */
export function techniqueLabel(technique: LiveTechnique | null): string | null {
  if (!technique) return null;
  const family = FAMILY[technique.family] ?? technique.family.replaceAll("_", " ");
  if (!technique.mutator) return family;
  const mutator = MUTATOR[technique.mutator] ?? technique.mutator.replaceAll("_", " ");
  return `${family} · ${mutator}`;
}

export const KIND: Record<SessionKind, { label: string; cls: string }> = {
  audience: { label: "Público", cls: "audience" },
  swarm: { label: "Agente simulado", cls: "swarm" },
  prober: { label: "Prober", cls: "prober" },
};

export const ROUTE: Record<RouteName, { label: string; cls: string }> = {
  honeypot: { label: "Ruta: señuelo", cls: "r-honeypot" },
  protected: { label: "Ruta: protegida", cls: "r-protected" },
};
