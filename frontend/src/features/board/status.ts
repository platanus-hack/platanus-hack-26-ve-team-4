import type { CarouselItem, ChatStatus, LiveAttempt, LiveSession } from "./types";

export const TERMINAL = new Set(["evaluated", "inconclusive"]);
export const isPending = (attempt: LiveAttempt) => !TERMINAL.has(attempt.status);

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/**
 * Estado del chat (franja bajo la cabecera), con la regla de la maqueta:
 * "Bloqueado" solo con un `prevented` o un parche vigente; "No logrado" e "Inconcluso" no son
 * mérito de la defensa. Un chat enmascarado nunca revela su resultado.
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
  if (session.concealed)
    return { tone: "neutral", label: "Atacando", detail: "Oculto hasta revelar" };
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
  const last = done.at(-1);
  if (!last) return { tone: "neutral", label: "Atacando", detail: "Primer intento" };
  if (last.outcome === "prevented") {
    const prevented = session.prevented_n ?? 1;
    return {
      tone: "blocked",
      label: "Bloqueado",
      detail: plural(prevented, "frenado", "frenados"),
    };
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
 * Lo que el carrusel muestra de cada chat. El `pulseKey` de un chat enmascarado solo cambia con la
 * actividad (nuevo intento o cambio de estado del intento), nunca con su desenlace.
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
    pulseKey: session.concealed ? activity : `${status.tone}:${activity}`,
  };
}

/** "ahora", "hace N s" o "hace N min", contra el reloj del servidor (`generated_at`). */
export function ago(since: string, now: string): string {
  const seconds = Math.max(0, Math.round((Date.parse(now) - Date.parse(since)) / 1000));
  if (!Number.isFinite(seconds) || seconds < 2) return "ahora";
  if (seconds < 60) return `hace ${seconds} s`;
  return `hace ${Math.floor(seconds / 60)} min`;
}
