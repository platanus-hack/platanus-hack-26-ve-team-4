// Lote de mensajes del participante: lo que escribe seguido sale junto en un solo intento.
// Para el participante es un chat normal: ve sus mensajes enviados y, a los pocos segundos, que
// Yummy está escribiendo. No ve espera, contador ni marca de pendiente.

/** Silencio tras el último mensaje antes de enviar el lote; cada mensaje lo reinicia. */
export const BATCH_IDLE_MS = 10_000;
/** Silencio tras el último mensaje antes de mostrar «escribiendo…». */
export const TYPING_DELAY_MS = 4_000;
/** Mensajes sin respuesta que admite el lote; al llegar, sale y el chat pide esperar a Yummy. */
export const QUEUE_MAX = 10;

export interface PendingBatch {
  texts: string[];
  /** Instantes (ms epoch) del primer y del último mensaje. */
  first: number;
  last: number;
}

export function addToBatch(batch: PendingBatch | null, text: string, at: number): PendingBatch {
  if (!batch) return { texts: [text], first: at, last: at };
  return { ...batch, texts: [...batch.texts, text], last: at };
}

export function isDue(batch: PendingBatch, now: number, max: number, idle: number): boolean {
  return batch.texts.length >= max || now >= batch.last + idle;
}

/** Un solo mensaje unido con saltos de línea; si no cabe, grupos que respetan el largo máximo. */
export function packBatch(texts: string[], maxLength: number): string[] {
  const packed: string[] = [];
  for (const text of texts) {
    const last = packed.at(-1);
    if (last !== undefined && last.length + 1 + text.length <= maxLength) {
      packed[packed.length - 1] = `${last}\n${text}`;
    } else packed.push(text);
  }
  return packed;
}

export function isBatch(value: unknown): value is PendingBatch {
  const batch = value as PendingBatch | null;
  return Boolean(
    batch &&
      Array.isArray(batch.texts) &&
      batch.texts.length > 0 &&
      batch.texts.length <= QUEUE_MAX &&
      batch.texts.every((text) => typeof text === "string" && text.trim() !== "") &&
      Number.isFinite(batch.first) &&
      Number.isFinite(batch.last),
  );
}
