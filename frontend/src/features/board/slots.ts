import type { LiveSession } from "./types";

export type TileState = "leaked" | "safe" | "blocked" | "neutral";

/** Estado visual de una sesión. Si la ruta está oculta (público sin revelar) no hay azul. */
export function tileState(session: LiveSession): TileState {
  if (session.route === "honeypot") return "safe";
  if (session.attempts.some((attempt) => attempt.outcome === "confirmed_violation"))
    return "leaked";
  const last = [...session.attempts].reverse().find((attempt) => attempt.outcome !== null);
  if (last && ["prevented", "not_achieved"].includes(last.outcome ?? "")) return "blocked";
  return "neutral";
}

/**
 * Mantiene cada sesión en su casilla. Las nuevas ocupan un hueco libre y, si no lo hay,
 * reemplazan a la casilla sin fijar con la actividad más antigua (solo si la nueva es más reciente).
 */
export function assignSlots(
  previous: string[],
  known: Map<string, LiveSession>,
  pinned: ReadonlySet<string>,
  count: number,
): string[] {
  const slots = previous.filter((id) => known.has(id)).slice(0, count);
  const incoming = [...known.values()]
    .filter((session) => !slots.includes(session.session_id))
    .sort((a, b) => b.last_activity.localeCompare(a.last_activity));
  for (const session of incoming) {
    if (slots.length < count) {
      slots.push(session.session_id);
      continue;
    }
    let oldest = -1;
    for (const [index, id] of slots.entries()) {
      if (pinned.has(id)) continue;
      const activity = known.get(id)?.last_activity ?? "";
      if (oldest === -1 || activity < (known.get(slots[oldest] ?? "")?.last_activity ?? ""))
        oldest = index;
    }
    if (oldest === -1) break;
    const current = known.get(slots[oldest] ?? "");
    if (current && session.last_activity > current.last_activity)
      slots[oldest] = session.session_id;
  }
  return slots;
}
