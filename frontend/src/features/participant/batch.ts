// Lote de mensajes del participante: una ráfaga se junta y viaja en un solo intento.

/** Espera sin mensajes nuevos antes de enviar el lote; cada mensaje la reinicia. */
export const BATCH_IDLE_MS = 10_000;
/** Tope desde el primer mensaje del lote, aunque se siga escribiendo. */
export const BATCH_MAX_WAIT_MS = 20_000;
/** Mensajes que cierran el lote; coincide con `max_messages` del intento. */
export const BATCH_MAX_MESSAGES = 4;

export interface PendingBatch {
  texts: string[];
  /** Instantes (ms epoch) del primer y del último mensaje. */
  first: number;
  last: number;
  /** «Enviar ahora»: no espera el contador. */
  now?: boolean;
}

export function addToBatch(batch: PendingBatch | null, text: string, at: number): PendingBatch {
  if (!batch) return { texts: [text], first: at, last: at };
  return { ...batch, texts: [...batch.texts, text], last: at };
}

export function dueAt(batch: PendingBatch): number {
  return Math.min(batch.last + BATCH_IDLE_MS, batch.first + BATCH_MAX_WAIT_MS);
}

export function isDue(batch: PendingBatch, now: number, max = BATCH_MAX_MESSAGES): boolean {
  return Boolean(batch.now) || batch.texts.length >= max || now >= dueAt(batch);
}

/** Un solo mensaje unido con saltos de línea; si supera el largo máximo, uno por mensaje. */
export function packBatch(texts: string[], maxLength: number): string[] {
  const joined = texts.join("\n");
  return joined.length <= maxLength ? [joined] : [...texts];
}

export function isBatch(value: unknown): value is PendingBatch {
  const batch = value as PendingBatch | null;
  return Boolean(
    batch &&
      Array.isArray(batch.texts) &&
      batch.texts.length > 0 &&
      batch.texts.length <= BATCH_MAX_MESSAGES &&
      batch.texts.every((text) => typeof text === "string" && text.trim() !== "") &&
      Number.isFinite(batch.first) &&
      Number.isFinite(batch.last) &&
      (batch.now === undefined || typeof batch.now === "boolean"),
  );
}
