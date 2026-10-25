import { useCallback, useEffect, useRef, useState } from "react";
import { addToBatch, BATCH_MAX_MESSAGES, dueAt, isDue, type PendingBatch } from "./batch";
import { loadBatch, saveBatch } from "./storage";

// Refresco del contador visible; el envío se decide con la hora real, no con los ticks.
const TICK_MS = 250;

/**
 * Lote pendiente del chat. Los mensajes se guardan en el navegador al agregarse y el lote se
 * entrega a `send` cuando vence (o se pide «Enviar ahora») y `canSend` lo permite: un intento a
 * la vez, porque el servidor admite una sola ejecución pendiente por sesión.
 */
export function useBatch(
  sessionId: string,
  send: (texts: string[]) => boolean,
  canSend: boolean,
  max = BATCH_MAX_MESSAGES,
) {
  const [batch, setBatch] = useState<PendingBatch | null>(() => loadBatch(sessionId));
  const [now, setNow] = useState(Date.now);
  // Copia síncrona: dos envíos del formulario en el mismo evento ven el lote actualizado.
  const current = useRef(batch);
  const sender = useRef(send);
  sender.current = send;

  const update = useCallback(
    (next: PendingBatch | null) => {
      current.current = next;
      saveBatch(sessionId, next);
      setBatch(next);
    },
    [sessionId],
  );

  useEffect(() => {
    if (!batch) return;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(timer);
  }, [batch]);

  const ready = batch !== null && isDue(batch, now, max);
  useEffect(() => {
    const pending = current.current;
    if (!ready || !canSend || !pending) return;
    if (sender.current(pending.texts)) update(null);
  }, [ready, canSend, update]);

  function add(text: string): boolean {
    const value = text.trim();
    const previous = current.current;
    if (!value || (previous && previous.texts.length >= max)) return false;
    const at = Date.now();
    setNow(at);
    update(addToBatch(previous, value, at));
    return true;
  }

  return {
    texts: batch?.texts ?? [],
    ready,
    full: (batch?.texts.length ?? 0) >= max,
    /** Segundos hasta que el lote venza. */
    remaining: batch ? Math.max(0, Math.ceil((dueAt(batch) - now) / 1000)) : 0,
    add,
    sendNow: () => {
      if (current.current) update({ ...current.current, now: true });
    },
  };
}
