import { useCallback, useEffect, useRef, useState } from "react";
import {
  addToBatch,
  BATCH_IDLE_MS,
  isDue,
  type PendingBatch,
  QUEUE_MAX,
  TYPING_DELAY_MS,
} from "./batch";
import { loadBatch, saveBatch } from "./storage";

/**
 * Lote del chat. Los mensajes se guardan en el navegador al agregarse y el lote sale a los
 * `BATCH_IDLE_MS` del último mensaje (o al llegar a `max`) cuando `canSend` lo permite: un intento
 * a la vez, porque el servidor admite una sola ejecución pendiente por sesión. A los
 * `TYPING_DELAY_MS` del último mensaje el chat muestra «escribiendo…».
 */
export function useBatch(
  sessionId: string,
  send: (texts: string[]) => boolean,
  canSend: boolean,
  max = QUEUE_MAX,
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

  // Despierta justo al mostrar «escribiendo…» y al vencer el lote; sin ticks visibles. Si el
  // navegador demoró la alarma (pestaña en segundo plano) y ya pasó la marca, se pone al día.
  useEffect(() => {
    if (!batch) return;
    const at = Date.now();
    const marks = [batch.last + TYPING_DELAY_MS, batch.last + BATCH_IDLE_MS];
    if (marks.some((mark) => now < mark && at >= mark)) {
      setNow(at);
      return;
    }
    const next = marks.filter((mark) => mark > at);
    if (!next.length) return;
    const timer = setTimeout(() => setNow(Date.now()), Math.min(...next) - at);
    return () => clearTimeout(timer);
  }, [batch, now]);

  const ready = batch !== null && isDue(batch, now, max, BATCH_IDLE_MS);
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
    full: (batch?.texts.length ?? 0) >= max,
    /** Yummy «escribe» desde los `TYPING_DELAY_MS` del último mensaje hasta que sale el lote. */
    typing: batch !== null && now >= batch.last + TYPING_DELAY_MS,
    add,
  };
}
