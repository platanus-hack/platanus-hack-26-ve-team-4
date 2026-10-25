import type {
  CarouselItem,
  ChatStatus,
  LiveAttempt,
  LiveDenial,
  LiveSession,
  SessionKind,
} from "./types";
import { denialLabel } from "./vocabulary";

export const TERMINAL = new Set(["evaluated", "inconclusive"]);
export const isPending = (attempt: LiveAttempt) => !TERMINAL.has(attempt.status);

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

const ATTACK_AGENTS = new Set<SessionKind>(["swarm", "prober"]);

/** Autor de las burbujas: el enjambre y el Prober atacan por diseño; a una persona se la presume de buena fe. */
export function speakerLabel(kind: SessionKind): string {
  return ATTACK_AGENTS.has(kind) ? "Atacante" : "Participante";
}

/**
 * Señal del sistema: una herramienta negada por un validador. "rate_limited" (control null) y
 * "pedido_inexistente" (puede ser un pedido mal escrito) no cuentan. Es una aproximación de vista a
 * routing/session_risk.py: el tablero no sabe si un pedido inexistente es un error de tipeo.
 */
const isRiskDenial = (d: LiveDenial) => d.control !== null && d.control !== "pedido_inexistente";

/**
 * Estado del chat (franja bajo la cabecera), con la regla de la maqueta:
 * "Bloqueado" solo con un `prevented` o un parche vigente; "No logrado" e "Inconcluso" no son
 * mérito de la defensa.
 * Buena fe: a una persona (Público) se la presume de buena fe; "Atacando" solo describe al
 * enjambre y al Prober, y el Público pasa a "Señal de riesgo" únicamente con una negación de validador.
 */
export function chatStatus(
  session: LiveSession,
  accepting: boolean,
  revealed: boolean,
): ChatStatus {
  const { attempts } = session;
  const busy = attempts.some(isPending);
  if (session.kind !== "prober" && !accepting && !revealed && !busy)
    return { tone: "neutral", label: "Acceso cerrado", detail: "Sin nuevos intentos" };
  const done = attempts.filter((attempt) => !isPending(attempt));
  const leak = [...done].reverse().find((a) => a.outcome === "confirmed_violation");
  if (leak && !leak.patched_by) {
    const objective = leak.violated_objectives[0];
    return {
      tone: "leak",
      label: "Se filtró",
      detail: `${objective ? `${objective} · ` : ""}intento ${leak.number}`,
    };
  }
  if (session.route === "honeypot") {
    const contained = session.contained_n ?? 0;
    return {
      tone: "safe",
      label: "En espacio seguro",
      detail: plural(contained, "contenido", "contenidos"),
    };
  }
  const patch = [...done].reverse().find((a) => a.patched_by)?.patched_by;
  if (patch)
    return { tone: "blocked", label: "Bloqueado", detail: `Parche v${patch.version} vigente` };
  const agent = ATTACK_AGENTS.has(session.kind);
  const last = done.at(-1);
  if (!last)
    return agent
      ? { tone: "neutral", label: "Atacando", detail: "Primer intento" }
      : { tone: "neutral", label: "Conversando", detail: "Primer mensaje" };
  if (last.outcome === "prevented") {
    const prevented = session.prevented_n ?? 1;
    return {
      tone: "blocked",
      label: "Bloqueado",
      detail: plural(prevented, "frenado", "frenados"),
    };
  }
  if (!agent) {
    const signal = [...done].reverse().find((a) => a.denials.some(isRiskDenial));
    const denial = signal?.denials.find(isRiskDenial);
    if (signal && denial)
      return {
        tone: "neutral",
        label: "Señal de riesgo",
        detail: `${denialLabel(denial)} · intento ${signal.number}`,
      };
    return { tone: "neutral", label: "Conversando", detail: "Sin señales de riesgo" };
  }
  const word =
    last.outcome === "not_achieved"
      ? "no logrado"
      : last.outcome === "contained_honeypot"
        ? "contenido"
        : "inconcluso";
  return { tone: "neutral", label: "Atacando", detail: `Último: ${word}` };
}

/** Alias corto para el indicador de la barra (el Prober se distingue por el final de su id). */
export function shortAlias(session: LiveSession): string {
  return session.kind === "prober" ? `P·${session.session_id.slice(-4)}` : session.alias;
}

/**
 * Lo que el carrusel muestra de cada chat. El `pulseKey` cambia con el tono y con la actividad
 * (nuevo intento o cambio de estado del intento).
 */
export function carouselItem(
  session: LiveSession,
  accepting: boolean,
  revealed: boolean,
): CarouselItem {
  const status = chatStatus(session, accepting, revealed);
  const last = session.attempts.at(-1);
  const activity = `${session.attempt_total}:${last?.status ?? ""}`;
  return {
    id: session.session_id,
    label: session.alias,
    short: shortAlias(session),
    tone: status.tone,
    title: `${session.alias}: ${status.label} · ${status.detail}`,
    pulseKey: `${status.tone}:${activity}`,
  };
}

/** "ahora", "hace N s" o "hace N min", contra el reloj del servidor (`generated_at`). */
export function ago(since: string, now: string): string {
  const seconds = Math.max(0, Math.round((Date.parse(now) - Date.parse(since)) / 1000));
  if (!Number.isFinite(seconds) || seconds < 2) return "ahora";
  if (seconds < 60) return `hace ${seconds} s`;
  return `hace ${Math.floor(seconds / 60)} min`;
}
