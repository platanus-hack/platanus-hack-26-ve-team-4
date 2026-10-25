import { Fragment, useEffect, useRef, useState } from "react";
import { ago, chatStatus, isPending } from "./status";
import type { LiveAttempt, LiveSession } from "./types";
import {
  denialLabel,
  KIND,
  outcomeView,
  ROUTE,
  techniqueLabel,
  UNKNOWN_OUTCOME,
} from "./vocabulary";

/** Intentos que se dibujan en la conversación (los más recientes; el resto queda fuera de vista). */
const SHOWN = 8;
/** Segmentos de la barra de progreso del pie. */
const PROGRESS = 10;
const EVENT_MS = 4000;

const LockIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <rect x="4.5" y="10.5" width="15" height="10" rx="2" />
    <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
  </svg>
);
export const PinIcon = ({ size = 18, className }: { size?: number; className?: string }) => (
  <svg
    className={className}
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M12 17v5" />
    <path d="M9 3h6l-1 6 4 4v2H6v-2l4-4-1-6Z" />
  </svg>
);

interface Props {
  session: LiveSession;
  index: number;
  total: number;
  pinned: boolean;
  inView: boolean;
  accepting: boolean;
  revealed: boolean;
  /** Reloj del servidor (`generated_at`): "hace N s" no depende del reloj del navegador. */
  now: string;
  onTogglePin: (id: string) => void;
}

function Turn({
  attempt,
  masked,
  previous,
}: {
  attempt: LiveAttempt;
  masked: boolean;
  previous?: LiveAttempt;
}) {
  const technique = masked ? null : techniqueLabel(attempt.technique);
  const diverted =
    !masked &&
    attempt.route === "honeypot" &&
    (previous ? previous.route !== "honeypot" : attempt.number === 1);
  const pending = isPending(attempt);
  const outcome = outcomeView(attempt);
  return (
    <>
      {diverted && (
        <li className="av-sys safe">Desviado a espacio seguro · int. {attempt.number}</li>
      )}
      <li className="av-msg atk">
        <div className="av-meta">
          <span>Atacante</span>
          {technique && <span className="av-tech">{technique}</span>}
        </div>
        {attempt.messages.map((message, turn) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: los turnos de un intento no cambian.
          <p className="av-bubble" key={turn}>
            {message}
          </p>
        ))}
      </li>
      {pending ? (
        <li className="av-typing" role="status">
          <span className="dots" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>Bot escribiendo…</span>
        </li>
      ) : (
        <>
          {masked ? (
            <li className="av-msg bot">
              <p className="av-bubble masked">Respuesta oculta hasta revelar</p>
            </li>
          ) : (
            (attempt.reply || attempt.denials.length > 0) && (
              <li className="av-msg bot">
                {attempt.reply && <p className="av-bubble">{attempt.reply}</p>}
                {attempt.denials.map((denial, n) => (
                  // biome-ignore lint/suspicious/noArrayIndexKey: las negaciones de un intento no cambian.
                  <span className="av-denial" key={n}>
                    <LockIcon />
                    <span>Herramienta negada · {denialLabel(denial)}</span>
                  </span>
                ))}
              </li>
            )
          )}
          <li className={`av-chip ${masked ? "o-masked" : outcome.cls}`}>
            <span className="n">Intento {attempt.number} ·</span>
            {masked ? " resultado oculto" : ` ${outcome.text(attempt)}`}
          </li>
          {!masked && attempt.patched_by && (
            <li className="av-sys">
              Parche v{attempt.patched_by.version} activado ·{" "}
              {Math.round(attempt.patched_by.seconds_after)} s después
            </li>
          )}
        </>
      )}
    </>
  );
}

export function ChatTile({
  session,
  index,
  total,
  pinned,
  inView,
  accepting,
  revealed,
  now,
  onTogglePin,
}: Props) {
  const status = chatStatus(session, accepting, revealed);
  const masked = session.concealed;
  const kind = KIND[session.kind];
  const route = !masked && session.route ? ROUTE[session.route] : null;
  const shown = session.attempts.slice(-SHOWN);
  const offset = session.attempts.length - shown.length;
  const last = session.attempts.at(-1);

  // Evento: cuando cambia el estado, borde grueso 4 s y dos pulsos de anillo.
  const [event, setEvent] = useState(false);
  const previous = useRef(status.tone);
  useEffect(() => {
    if (previous.current === status.tone) return;
    previous.current = status.tone;
    setEvent(true);
    const timer = setTimeout(() => setEvent(false), EVENT_MS);
    return () => clearTimeout(timer);
  }, [status.tone]);

  const progress = session.attempts.slice(-PROGRESS);
  return (
    <section
      className={`av-chat st-${status.tone}${event ? " evt" : ""}`}
      aria-label={`Chat ${index + 1} de ${total}: ${session.alias}`}
      data-tone={status.tone}
      inert={!inView}
    >
      <div className="av-chead">
        <div className="av-row1">
          <h2 className="av-alias">{session.alias}</h2>
          <button
            type="button"
            className={`av-pin${pinned ? " on" : ""}`}
            aria-pressed={pinned}
            onClick={() => onTogglePin(session.session_id)}
          >
            <PinIcon />
            <span>{pinned ? "Fijado" : "Fijar"}</span>
          </button>
        </div>
        <div className="av-row2">
          <span className={`av-badge ${kind.cls}`}>
            <i />
            {kind.label}
          </span>
          {route && <span className={`av-badge ${route.cls}`}>{route.label}</span>}
        </div>
      </div>
      <div className="av-status">
        <div className="lbl">
          <i />
          <span>{status.label}</span>
        </div>
        <div className="det">{status.detail}</div>
      </div>
      <ol className="av-conv" aria-label={`Conversación de ${session.alias}`}>
        {shown.map((attempt, n) => (
          <Fragment key={attempt.id}>
            <Turn attempt={attempt} masked={masked} previous={session.attempts[offset + n - 1]} />
          </Fragment>
        ))}
      </ol>
      <div className="av-cfoot">
        <span>
          {last ? (
            <>
              Intento <b>{last.number}</b> · {ago(session.last_activity, now)}
            </>
          ) : (
            "Sin intentos"
          )}
        </span>
        <span className="av-prog" aria-hidden="true">
          {Array.from({ length: PROGRESS }, (_, k) => {
            const attempt = progress[k];
            const cls = !attempt
              ? ""
              : isPending(attempt)
                ? "run"
                : masked
                  ? "done"
                  : (outcomeView(attempt) ?? UNKNOWN_OUTCOME).seg;
            // biome-ignore lint/suspicious/noArrayIndexKey: los segmentos son posiciones fijas.
            return <i key={k} className={`av-seg${cls ? ` ${cls}` : ""}`} />;
          })}
        </span>
      </div>
    </section>
  );
}
