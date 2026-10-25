import type { MonitorAttempt, Outcome } from "./types";

export const OUTCOMES: Record<Outcome | "pending", { label: string; tone: string }> = {
  confirmed_violation: { label: "Violación", tone: "danger" },
  prevented: { label: "Impedido", tone: "accent" },
  contained_honeypot: { label: "Señuelo", tone: "decoy" },
  not_achieved: { label: "Sin hallazgos", tone: "muted" },
  inconclusive: { label: "Inconcluso", tone: "warn" },
  pending: { label: "En curso", tone: "muted" },
};

const FAMILIES: Record<string, string> = {
  direct_injection: "Inyección directa",
  indirect_injection: "Inyección indirecta",
  goal_hijacking: "Secuestro de objetivos",
  tool_misuse: "Uso indebido de herramientas",
  tool_poisoning: "Contaminación de herramienta",
  memory_poisoning: "Contaminación de memoria",
};

/** Señales de intención: etiquetas de auditoría, no acusaciones; el desenlace sigue siendo el del oráculo. */
export const SIGNALS: Record<string, string> = {
  data_request: "Pidió datos de pedidos o de otros",
  template_markup: "Marcado de plantilla de chat",
  rules_probe: "Preguntó por las reglas internas",
  off_scope: "Pidió algo fuera de soporte",
  off_scope_reply: "El agente respondió fuera de su papel",
};

export const signalLabel = (signal: string) => SIGNALS[signal] ?? signal;

export const ORIGINS: Record<string, string> = { audience: "audiencia", autonomous: "prober" };

export function outcomeOf(attempt: MonitorAttempt) {
  return OUTCOMES[attempt.outcome ?? "pending"];
}

export function familyOf(attempt: MonitorAttempt): string {
  if (attempt.route === "honeypot") return "Sesión desviada";
  if (attempt.family) return FAMILIES[attempt.family] ?? attempt.family;
  const [signal] = attempt.signals ?? [];
  if (attempt.outcome === "not_achieved" && signal) return `Señal: ${signalLabel(signal)}`;
  return attempt.outcome === "not_achieved" ? "Sin objetivo adversario" : "Sin clasificar";
}

const TIME = new Intl.DateTimeFormat("es", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});
export const NUMBER = new Intl.NumberFormat("es");

export function clock(iso: string): string {
  return TIME.format(new Date(iso));
}

export function totalTokens(attempt: MonitorAttempt): number {
  return attempt.usage.input_tokens + attempt.usage.output_tokens;
}

/** El proveedor simulado no reporta uso: «sin medir» en vez de un cero engañoso. */
export function tokensText(attempt: MonitorAttempt): string {
  const total = totalTokens(attempt);
  return total || attempt.usage.measured_calls ? NUMBER.format(total) : "sin medir";
}

/** Segundos entre el cierre del intento y la activación del parche que lo corrige. */
export function patchDelay(attempt: MonitorAttempt): number | null {
  const activated = attempt.patch?.activated_at;
  if (!activated) return null;
  const seconds = (Date.parse(activated) - Date.parse(attempt.updated_at)) / 1000;
  return Number.isFinite(seconds) && seconds >= 0 ? Math.round(seconds) : null;
}

export function usd(value: number): string {
  return `US$${value.toLocaleString("es", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}`;
}
