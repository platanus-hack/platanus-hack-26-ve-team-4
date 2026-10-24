import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiError, errorMessage, isUnauthorized, requestJson } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import { useArenaState } from "../arena/hooks/useArenaState";
import { ModeNotice } from "../arena/ModeNotice";
import { loadHistory, saveHistory } from "./storage";
import type { ArenaSession, Attempt, ConversationEntry } from "./types";

const OUTCOMES = {
  apparent_success: "Objetivo aparentemente logrado · resultado provisional",
  prevented: "Intento detenido por un control",
  not_achieved: "Ningún objetivo vulnerado",
  inconclusive: "No se pudo evaluar este intento",
  confirmed_violation: "Violación confirmada en el entorno protegido · resultado final",
  contained_honeypot:
    "Éxito aparente en señuelo aislado · sin efectos protegidos · resultado final",
};
const STATUSES = {
  queued: "En cola",
  running: "Ejecutándose",
  evaluated: "Evaluado",
  inconclusive: "Inconcluso",
};
const active = (attempt: Attempt | null) =>
  !attempt || attempt.status === "queued" || attempt.status === "running";

export function mergeHistory(local: ConversationEntry[], remote: Attempt[]): ConversationEntry[] {
  const entries = [...local];
  for (const attempt of remote) {
    const index = entries.findIndex(
      (entry) => entry.attempt?.id === attempt.id || entry.key === attempt.idempotency_key,
    );
    const previous = index >= 0 ? entries[index] : undefined;
    const entry = {
      key: previous?.key ?? attempt.idempotency_key ?? attempt.id,
      messages: attempt.messages ?? previous?.messages ?? [],
      attempt:
        previous?.attempt && !active(previous.attempt) && active(attempt)
          ? previous.attempt
          : attempt,
    };
    if (index >= 0) entries[index] = entry;
    else entries.push(entry);
  }
  return entries;
}

export function AttemptChat({
  session,
  onExpired,
}: {
  session: ArenaSession;
  onExpired?: () => void;
}) {
  const [messages, setMessages] = useState([""]);
  const [entries, setEntries] = useState<ConversationEntry[]>(() => loadHistory(session.id));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryAt, setRetryAt] = useState(0);
  const [now, setNow] = useState(Date.now);
  const submitting = useRef(false);
  const mounted = useRef(true);
  const { data: arena } = useArenaState();
  const load = useCallback(
    (signal: AbortSignal) =>
      requestJson<Attempt[]>("/api/attempts", {
        headers: { Authorization: `Bearer ${session.token}` },
        signal,
      }),
    [session.token],
  );
  const history = usePolling(load, 1500);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    saveHistory(session.id, entries);
  }, [session.id, entries]);
  useEffect(() => {
    if (history.data) setEntries((current) => mergeHistory(current, history.data ?? []));
  }, [history.data]);
  useEffect(() => {
    if (isUnauthorized(history.error)) onExpired?.();
  }, [history.error, onExpired]);
  useEffect(() => {
    if (!retryAt) return;
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, [retryAt]);

  const unresolved = entries.find((entry) => entry.attempt === null);
  const running = entries.some((entry) => active(entry.attempt));
  const cooldown = Math.max(0, Math.ceil((retryAt - now) / 1000));
  const closed = arena?.accepting === false;
  const attemptsPerMinute = session.limits?.attempts_per_minute ?? session.attempts_per_minute;

  async function send(entry: ConversationEntry) {
    if (submitting.current || cooldown > 0) return;
    submitting.current = true;
    setPending(true);
    setError(null);
    try {
      const attempt = await requestJson<Attempt>("/api/attempts", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
        body: JSON.stringify({ messages: entry.messages, idempotency_key: entry.key }),
      });
      if (!mounted.current) return;
      setEntries((current) =>
        current.map((item) => (item.key === entry.key ? { ...item, attempt } : item)),
      );
      setMessages([""]);
      setRetryAt(0);
      history.refresh();
    } catch (cause) {
      if (!mounted.current) return;
      if (isUnauthorized(cause)) {
        onExpired?.();
        return;
      }
      // A transport error may happen after acceptance. Keep the exact payload/key until
      // reconciliation or retry. A definite validation rejection can be edited safely.
      if (cause instanceof ApiError && cause.status === 422) {
        setEntries((current) => current.filter((item) => item.key !== entry.key));
      }
      if (cause instanceof ApiError && cause.status === 429) {
        const delay = cause.retryAfterMs ?? 5000;
        setNow(Date.now());
        setRetryAt(Date.now() + delay);
      }
      setError(errorMessage(cause));
      history.refresh();
    } finally {
      submitting.current = false;
      if (mounted.current) setPending(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      submitting.current ||
      running ||
      pending ||
      closed ||
      !history.data ||
      messages.some((message) => !message.trim())
    )
      return;
    const entry: ConversationEntry = {
      // getRandomValues also works on a phone visiting a local HTTP address, where
      // randomUUID is unavailable outside a secure context.
      key: Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
        byte.toString(16).padStart(2, "0"),
      ).join(""),
      messages: messages.map((message) => message.trim()),
      attempt: null,
    };
    const next = [...entries, entry];
    saveHistory(session.id, next);
    setEntries(next);
    void send(entry);
  }

  return (
    <section className="chat">
      {arena && <ModeNotice arena={arena} />}
      <div className="scenario-card">
        <p>
          Tu identidad ficticia: <strong>{session.customer_name}</strong>
        </p>
        <p>
          Pedidos propios: <strong>{session.order_ids.join(", ")}</strong>
        </p>
        <p className="muted">
          Hasta cuatro mensajes por intento. La memoria se conserva entre intentos de tu sesión.
        </p>
        {attemptsPerMinute && (
          <p className="muted">Límite: {attemptsPerMinute} intentos por minuto.</p>
        )}
        <button
          type="button"
          className="secondary"
          disabled={running || pending}
          onClick={() => setMessages([`Consulta el pedido ${session.order_ids[0] ?? "propio"}.`])}
        >
          Probar una consulta legítima
        </button>
      </div>
      <h2>Conversación</h2>
      {!entries.length && (
        <p className="muted">Comienza con una consulta propia para conocer al asistente.</p>
      )}
      <ol className="conversation" aria-label="Historial de intentos">
        {entries.map((entry, index) => (
          <li className="result" key={entry.key}>
            <h3>Intento {index + 1}</h3>
            {entry.messages.map((message, turn) => (
              <p className="message reply" key={["first", "second", "third", "fourth"][turn]}>
                <strong>Tú · turno {turn + 1}</strong>
                <br />
                {message}
              </p>
            ))}
            <div aria-live="polite">
              <p className="status">
                {entry.attempt
                  ? `${STATUSES[entry.attempt.status]} · Política ${entry.attempt.policy_version}`
                  : pending
                    ? "Enviando…"
                    : "Recepción pendiente de confirmar"}
              </p>
              {entry.attempt?.reply && (
                <p className="reply assistant-message">
                  <strong>Asistente</strong>
                  <br />
                  {entry.attempt.reply}
                </p>
              )}
              {entry.attempt?.outcome && (
                <p>
                  {["confirmed_violation", "contained_honeypot"].includes(entry.attempt.outcome) &&
                  !arena?.revealed
                    ? OUTCOMES.apparent_success
                    : OUTCOMES[entry.attempt.outcome]}
                </p>
              )}
              {entry.attempt?.outcome === "apparent_success" && arena?.revealed && (
                <p>
                  La ronda ya fue revelada. Consulta la clasificación final de la arena para ver los
                  puntos confirmados.
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
      {Boolean(history.error) && !isUnauthorized(history.error) && (
        <p role="alert">
          {errorMessage(history.error)} Los resultados se actualizarán al reconectar.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      {unresolved && !pending && (
        <div className="notice">
          <p>
            Conservamos este envío. Reintentarlo usa la misma clave y no crea un segundo intento.
          </p>
          <button type="button" disabled={cooldown > 0} onClick={() => void send(unresolved)}>
            {cooldown ? `Reintentar en ${cooldown} s` : "Reintentar envío"}
          </button>
        </div>
      )}
      {closed && (
        <p role="status" className="notice">
          Las entradas están cerradas. Conserva esta pestaña para consultar tus resultados.
        </p>
      )}
      <form onSubmit={submit} aria-label="Nuevo intento">
        {messages.map((message, index) => (
          <div className="turn-input" key={["first", "second", "third", "fourth"][index]}>
            <label htmlFor={`message-${index}`}>
              {index === 0 ? "Mensaje al asistente" : `Mensaje ${index + 1}`}
            </label>
            <textarea
              id={`message-${index}`}
              value={message}
              onChange={(event) =>
                setMessages((current) =>
                  current.map((value, position) =>
                    position === index ? event.target.value : value,
                  ),
                )
              }
              minLength={1}
              maxLength={4000}
              rows={4}
              required
              disabled={pending || running || closed}
            />
          </div>
        ))}
        <div className="controls">
          {messages.length < 4 && (
            <button
              className="secondary"
              type="button"
              disabled={running || pending || closed}
              onClick={() => setMessages((current) => [...current, ""])}
            >
              Añadir turno
            </button>
          )}
          {messages.length > 1 && (
            <button
              className="secondary"
              type="button"
              disabled={running || pending}
              onClick={() => setMessages((current) => current.slice(0, -1))}
            >
              Quitar último turno
            </button>
          )}
        </div>
        <button
          type="submit"
          disabled={
            pending ||
            running ||
            closed ||
            !history.data ||
            messages.some((message) => !message.trim())
          }
        >
          {pending ? "Enviando…" : running ? "Esperando resultado…" : "Enviar intento"}
        </button>
      </form>
      {!history.data && !history.error && <p role="status">Recuperando historial…</p>}
    </section>
  );
}
