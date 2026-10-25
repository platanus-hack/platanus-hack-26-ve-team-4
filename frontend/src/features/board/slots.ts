import type { LiveSession } from "./types";

/** Chats del carrusel, chats visibles a la vez y máximo de fijados (siempre queda 1 que se mueve). */
export const CHAT_COUNT = 8;
export const VISIBLE = 3;
export const MAX_PINS = 2;
/** Un chat (448 px) más la separación (24 px). */
export const STEP = 448 + 24;

/**
 * Mantiene cada sesión en su lugar del carrusel. Las nuevas ocupan un hueco libre y, si no lo hay,
 * reemplazan al lugar sin fijar con la actividad más antigua (solo si la nueva es más reciente).
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

/**
 * Fija o suelta un chat. Los fijados van del más antiguo al más nuevo; al fijar uno más del
 * máximo se suelta el más antiguo y se informa cuál (`released`).
 */
export function togglePin(
  order: readonly string[],
  id: string,
  max = MAX_PINS,
): { order: string[]; released: string | null } {
  if (order.includes(id)) return { order: order.filter((item) => item !== id), released: null };
  const next = [...order, id];
  const released = next.length > max ? (next.shift() ?? null) : null;
  return { order: next, released };
}

/** Ventana del carrusel: fijados a la izquierda y luego los que se mueven. */
export function windowOf(ids: readonly string[], pinned: readonly string[], index: number) {
  const pins = pinned.filter((id) => ids.includes(id));
  const free = ids.filter((id) => !pins.includes(id));
  const slots = Math.max(1, VISIBLE - pins.length);
  const maxIndex = Math.max(0, free.length - slots);
  const start = Math.max(0, Math.min(maxIndex, index));
  const visible = [...pins, ...free.slice(start, start + slots)];
  return { pins, free, slots, maxIndex, start, visible, order: [...pins, ...free] };
}

/** Índice que deja un chat a la vista: si ya se ve no se mueve; si no, queda al centro. */
export function focusIndex(free: readonly string[], id: string, start: number, slots: number) {
  const position = free.indexOf(id);
  if (position === -1 || (position >= start && position < start + slots)) return start;
  return position - Math.floor((slots - 1) / 2);
}

/** Marcos sobre los indicadores: uno por tramo contiguo de chats visibles (grilla de 8 × 153). */
export const INDICATOR = { width: 153, gap: 8 };
export function frames(order: readonly string[], visible: readonly string[]) {
  const runs: { from: number; to: number }[] = [];
  order.forEach((id, index) => {
    if (!visible.includes(id)) return;
    const last = runs.at(-1);
    if (last && last.to === index - 1) last.to = index;
    else runs.push({ from: index, to: index });
  });
  const pitch = INDICATOR.width + INDICATOR.gap;
  return runs.map(({ from, to }) => ({
    left: from * pitch - 4,
    width: (to - from + 1) * INDICATOR.width + (to - from) * INDICATOR.gap + 8,
  }));
}
