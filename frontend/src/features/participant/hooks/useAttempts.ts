import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../../shared/api/http";
import { listAttempts, submitAttempt } from "../api/attempts";
import type { Attempt } from "../types";

const POLL_MS = 1500;

function isOpen(attempt: Attempt) {
  return attempt.status === "queued" || attempt.status === "running";
}

export function describeError(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return "No hay conexión con la arena. Revisa tu red e inténtalo de nuevo.";
  }
  if (error.status === 429) {
    return `Espera ${error.retryAfter ?? 3} s antes de enviar otro intento.`;
  }
  if (error.status === 422) {
    return "Revisa el mensaje: hasta 4 turnos de 4000 caracteres, ninguno vacío.";
  }
  if (error.status === 503) {
    return error.detail ?? "La arena no acepta intentos en este momento.";
  }
  return "No pudimos enviar tu intento. Inténtalo de nuevo.";
}

export function useAttempts(token: string, onExpired: () => void) {
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  // Se conserva tras un fallo de red: reenviar con la misma clave no duplica el intento.
  const pendingKey = useRef<string | null>(null);

  const handleError = useCallback(
    (caught: unknown) => {
      if (caught instanceof ApiError && caught.status === 401) {
        onExpired();
        return;
      }
      setError(describeError(caught));
    },
    [onExpired],
  );

  const refresh = useCallback(async () => {
    try {
      setAttempts(await listAttempts(token));
    } catch (caught) {
      handleError(caught);
    }
  }, [token, handleError]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const hasOpen = attempts.some(isOpen);
  useEffect(() => {
    if (!hasOpen) {
      return;
    }
    const timer = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(timer);
  }, [hasOpen, refresh]);

  const submit = useCallback(
    async (messages: string[]): Promise<boolean> => {
      pendingKey.current ??= crypto.randomUUID();
      setSending(true);
      setError(null);
      try {
        const attempt = await submitAttempt(token, messages, pendingKey.current);
        pendingKey.current = null;
        setAttempts((current) => [attempt, ...current.filter((item) => item.id !== attempt.id)]);
        return true;
      } catch (caught) {
        if (caught instanceof ApiError) {
          pendingKey.current = null;
        }
        handleError(caught);
        return false;
      } finally {
        setSending(false);
      }
    },
    [token, handleError],
  );

  return { attempts, error, sending, submit };
}
