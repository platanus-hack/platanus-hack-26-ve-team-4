import { useCallback, useEffect, useRef, useState } from "react";
import { addToBatch, type PendingBatch, QUEUE_MAX } from "./batch";
import { loadBatch, saveBatch } from "./storage";

/**
 * Cola del chat. Los mensajes se guardan en el navegador al agregarse y salen apenas `canSend`
 * lo permite: un intento a la vez, porque el servidor admite una sola ejecución pendiente por
 * sesión. Lo que se escribe mientras Yummy responde sale junto en el intento siguiente.
 */
export function useBatch(
  sessionId: string,
  send: (texts: string[]) => boolean,
  canSend: boolean,
  max = QUEUE_MAX,
) {
  const [batch, setBatch] = useState<PendingBatch | null>(() => loadBatch(sessionId));
  // Copia síncrona: dos envíos del formulario en el mismo evento ven la cola actualizada.
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
    void batch;
    const pending = current.current;
    if (!canSend || !pending) return;
    if (sender.current(pending.texts)) update(null);
  }, [batch, canSend, update]);

  function add(text: string): boolean {
    const value = text.trim();
    const previous = current.current;
    if (!value || (previous && previous.texts.length >= max)) return false;
    update(addToBatch(previous, value, Date.now()));
    return true;
  }

  return {
    texts: batch?.texts ?? [],
    full: (batch?.texts.length ?? 0) >= max,
    add,
  };
}
