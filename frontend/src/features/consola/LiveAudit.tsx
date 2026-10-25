import { useCallback, useEffect } from "react";
import { ApiError, errorMessage, isUnauthorized } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import { Exchange } from "../audit/Exchange";
import { DIVERSIONS } from "../audit/labels";
import type { AuditAttempt, ChatDetail } from "../audit/types";
import { operatorRequest } from "../operator/api";
import "../monitor/monitor.css";
import "../audit/audit.css";
import "./consola.css";

const POLL_MS = 1500;
const GUIDE = "Escribe un mensaje en el chat: aquí verás cómo lo clasifica y qué hace el agente.";

interface Props {
  secret: string;
  sessionId: string;
  onUnauthorized: () => void;
}

function Summary({ chat }: { chat: ChatDetail }) {
  const honeypot = chat.route === "honeypot";
  const signals = chat.risk_signals ?? [];
  return (
    <>
      <div className="audit-class">
        <span className={`monitor-pill ${honeypot ? "tone-decoy" : "tone-muted"}`}>
          Ruta: {honeypot ? "Señuelo" : "Protegida"}
        </span>
        <span className="monitor-pill tone-muted">Riesgo: {chat.risk_score ?? 0}</span>
        <span className="monitor-pill tone-muted">{chat.violations} violación(es)</span>
        <span className="monitor-pill tone-muted">{chat.attempts} mensaje(s)</span>
      </div>
      {signals.length > 0 && (
        <p className="audit-note">
          Señales de riesgo:{" "}
          {signals.map((signal) => `${signal.validator} ×${signal.count}`).join(", ")}
        </p>
      )}
      {chat.diversion && (
        <p className="audit-note">
          Desviada al señuelo: {DIVERSIONS[chat.diversion.reason] ?? chat.diversion.reason}
        </p>
      )}
    </>
  );
}

/** Auditoría de la sesión interna que se refresca sola: el mensaje más reciente aparece primero. */
export function LiveAudit({ secret, sessionId, onUnauthorized }: Props) {
  const load = useCallback(
    (signal: AbortSignal) =>
      operatorRequest<ChatDetail>(
        secret,
        `/audit/chats/${encodeURIComponent(sessionId)}`,
        undefined,
        signal,
      ),
    [secret, sessionId],
  );
  const { data, error } = usePolling<ChatDetail>(load, POLL_MS);
  useEffect(() => {
    if (isUnauthorized(error)) onUnauthorized();
  }, [error, onUnauthorized]);

  // Un chat sin mensajes aún responde 404 en el backend: es un estado vacío, no un fallo.
  const notFound = error instanceof ApiError && error.status === 404;
  const attempts: AuditAttempt[] = data
    ? data.threads.flatMap((thread) => thread.attempts).reverse()
    : [];

  return (
    <section className="monitor-panel consola-audit" aria-label="Auditoría en vivo">
      <h2>Auditoría en vivo</h2>
      {!data && error === null && <p className="muted">Cargando auditoría…</p>}
      {!data && error !== null && !notFound && <p role="alert">{errorMessage(error)}</p>}
      {data && error !== null && (
        <p role="status" className="monitor-stale">
          {errorMessage(error)} Los datos pueden estar desactualizados.
        </p>
      )}
      {data && <Summary chat={data} />}
      {attempts.length === 0 && (data || notFound) && <p className="muted">{GUIDE}</p>}
      {attempts.length > 0 && (
        <ol className="audit-thread">
          {attempts.map((attempt) => (
            <Exchange key={attempt.id} live attempt={attempt} />
          ))}
        </ol>
      )}
    </section>
  );
}
