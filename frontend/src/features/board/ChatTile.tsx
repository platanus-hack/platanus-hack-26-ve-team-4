import { useEffect, useRef } from "react";
import { OUTCOMES } from "../operator/AttemptList";
import { tileState } from "./slots";
import type { LiveAttempt, LiveSession, SessionKind } from "./types";

const KINDS: Record<SessionKind, string> = {
  audience: "Público",
  swarm: "Agente simulado",
  prober: "Prober",
};
const STATE_LABELS = {
  leaked: "Se dejó pasar",
  safe: "Espacio seguro",
  blocked: "Bloqueado",
  neutral: "En curso",
};
// Cada caso del Prober abre su propia sesión: se distinguen por el final del identificador.
const displayName = (session: LiveSession) =>
  session.kind === "prober" ? `${session.alias} · ${session.session_id.slice(-4)}` : session.alias;
const pending = (attempt: LiveAttempt) => ["queued", "running"].includes(attempt.status);

interface Props {
  session: LiveSession | null;
  pinned: boolean;
  onTogglePin: (id: string) => void;
}

export function ChatTile({ session, pinned, onTogglePin }: Props) {
  const scroller = useRef<HTMLOListElement>(null);
  const last = session?.attempts.at(-1);
  // biome-ignore lint/correctness/useExhaustiveDependencies: el desplazamiento sigue al último mensaje.
  useEffect(() => {
    const element = scroller.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [session?.attempts.length, last?.status, last?.reply]);

  if (!session)
    return (
      <article className="tile tile-empty" aria-label="Casilla libre">
        <p className="muted">Esperando un atacante…</p>
      </article>
    );
  const state = tileState(session);
  const name = displayName(session);
  return (
    <article
      className={`tile tile-${state}`}
      aria-label={`Chat de ${name}`}
      data-state={state}
      data-pinned={pinned}
      onClick={() => onTogglePin(session.session_id)}
      onKeyDown={undefined}
    >
      <header>
        <h2>{name}</h2>
        <span className={`badge badge-${session.kind}`}>{KINDS[session.kind]}</span>
        {session.route && (
          <span className={`badge ${session.route === "honeypot" ? "badge-safe" : "badge-route"}`}>
            {session.route === "honeypot" ? "Espacio seguro" : "Protegido"}
          </span>
        )}
        <span className={`state state-${state}`}>{STATE_LABELS[state]}</span>
        <button
          type="button"
          className="pin"
          aria-pressed={pinned}
          onClick={(event) => {
            event.stopPropagation();
            onTogglePin(session.session_id);
          }}
        >
          {pinned ? "Fijada" : "Fijar"}
        </button>
      </header>
      <ol className="transcript" ref={scroller} aria-label={`Conversación de ${name}`}>
        {session.attempts.map((attempt) => (
          <li key={attempt.id}>
            {attempt.messages.map((message, turn) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: los turnos del intento son estables.
              <p className="line attacker" key={turn}>
                <strong>{name}</strong>
                {message}
              </p>
            ))}
            {pending(attempt) ? (
              <p className="line bot typing" role="status">
                Asistente escribiendo…
              </p>
            ) : (
              attempt.reply && (
                <p className="line bot">
                  <strong>Asistente</strong>
                  {attempt.reply}
                </p>
              )
            )}
            {attempt.outcome && (
              <span className={`chip chip-${attempt.outcome}`}>
                {OUTCOMES[attempt.outcome] ?? attempt.outcome}
              </span>
            )}
          </li>
        ))}
      </ol>
    </article>
  );
}
