import { Fragment } from "react";
import { Exchange } from "./Exchange";
import { DIVERSIONS, KINDS, moment } from "./labels";
import type { ChatDetail } from "./types";

export function ChatAudit({ chat }: { chat: ChatDetail }) {
  const firstDiverted = chat.threads
    .flatMap((thread) => thread.attempts)
    .find((attempt) => attempt.route === "honeypot")?.id;
  const meta: [string, string][] = [
    ["Tipo", KINDS[chat.kind]],
    ["Cliente ficticio", chat.customer_id],
    ["Ruta", chat.route === "honeypot" ? "Señuelo" : "Protegida"],
    ["Mensajes", String(chat.attempts)],
    ["Conversaciones", String(chat.conversations)],
    ["Inicio", moment(chat.created_at)],
  ];
  return (
    <section className="monitor-panel audit-chat" aria-label="Historial del chat">
      <div className="monitor-row">
        <div>
          <span className="monitor-label">Sesión {chat.id}</span>
          <h2>{chat.alias}</h2>
        </div>
        {chat.violations > 0 && (
          <span className="monitor-pill tone-danger">
            {chat.violations} {chat.violations === 1 ? "violación" : "violaciones"}
          </span>
        )}
      </div>
      <dl className="monitor-meta">
        {meta.map(([key, value]) => (
          <div key={key}>
            <dt className="monitor-label">{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {chat.threads.length === 0 && <p className="muted">Esta sesión no envió mensajes.</p>}
      <ol className="audit-threads">
        {chat.threads.map((thread) => (
          <li key={thread.index}>
            <h3 className="audit-divider">Conversación {thread.index}</h3>
            <ol className="audit-thread">
              {thread.attempts.map((attempt) => (
                <Fragment key={attempt.id}>
                  {attempt.id === firstDiverted && chat.diversion && (
                    <li className="audit-diversion" role="note">
                      Desviada al señuelo el {moment(chat.diversion.at)}:{" "}
                      {DIVERSIONS[chat.diversion.reason] ?? chat.diversion.reason}.
                    </li>
                  )}
                  <Exchange attempt={attempt} />
                </Fragment>
              ))}
            </ol>
          </li>
        ))}
      </ol>
    </section>
  );
}
