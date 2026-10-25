import { Fragment } from "react";
import { OUTCOMES } from "../monitor/labels";
import { DIVERSIONS, KINDS, moment, OBJECTIVES, STEPS, seconds } from "./labels";
import type { AuditAttempt, ChatDetail, ToolStep } from "./types";

function json(value: Record<string, unknown>): string {
  return Object.keys(value).length ? JSON.stringify(value, null, 2) : "—";
}

function Step({ step }: { step: ToolStep }) {
  const kind = STEPS[step.kind] ?? { label: step.kind, tone: "muted" };
  const effect = typeof step.effect.kind === "string" ? step.effect.kind : null;
  return (
    <li className="audit-step">
      <div className="monitor-row">
        <span>
          <span className={`monitor-pill tone-${kind.tone}`}>{kind.label}</span>{" "}
          <code>{step.tool}</code>
        </span>
        <span className="monitor-label">evento {step.event_id}</span>
      </div>
      {step.validator && (
        <p className="audit-note">
          Control: <code>{step.validator}</code>
        </p>
      )}
      {effect && effect !== "none" && (
        <p className="audit-note">
          Efecto: <code>{effect}</code>
        </p>
      )}
      <details>
        <summary>Argumentos, procedencia y salida</summary>
        <dl className="audit-json">
          <dt>Argumentos</dt>
          <dd>
            <pre>{json(step.arguments)}</pre>
          </dd>
          <dt>Procedencia</dt>
          <dd>
            <pre>{json(step.provenance)}</pre>
          </dd>
          {Object.keys(step.effect).length > 0 && (
            <>
              <dt>Efecto</dt>
              <dd>
                <pre>{json(step.effect)}</pre>
              </dd>
            </>
          )}
          <dt>Salida</dt>
          <dd>
            <pre>{json(step.output)}</pre>
          </dd>
        </dl>
      </details>
    </li>
  );
}

function Exchange({ attempt }: { attempt: AuditAttempt }) {
  const outcome = OUTCOMES[attempt.outcome ?? "pending"];
  const violated = attempt.verdicts.filter((verdict) => verdict.violated);
  return (
    <li
      className={`audit-exchange tone-${outcome.tone}`}
      aria-label={`Mensaje ${attempt.position}`}
    >
      <div className="audit-exchange-head">
        <span className="monitor-label">
          #{attempt.position} · {moment(attempt.created_at)} · v{attempt.policy_version} ·{" "}
          {attempt.route === "honeypot" ? "señuelo" : "protegido"} ·{" "}
          {seconds(attempt.duration_seconds)}
        </span>
        <span className={`monitor-pill tone-${outcome.tone}`}>{outcome.label}</span>
      </div>
      {attempt.messages.map((message, index) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: los turnos no tienen otro identificador.
        <p key={index} className="bubble bubble--user">
          <span className="visually-hidden">Participante: </span>
          {message}
        </p>
      ))}
      {attempt.reply ? (
        <p className="bubble bubble--bot">
          <span className="visually-hidden">Yummy: </span>
          {attempt.reply}
        </p>
      ) : (
        <p className="audit-note">Sin respuesta ({attempt.status}).</p>
      )}
      {violated.length > 0 && (
        <p className="audit-note audit-violation">
          Objetivo vulnerado:{" "}
          {violated
            .map((verdict) => OBJECTIVES[verdict.objective_id] ?? verdict.objective_id)
            .join(", ")}
          {violated[0]?.detail ? ` — ${violated[0].detail}` : ""}
        </p>
      )}
      <details className="audit-trace">
        <summary>
          Traza · {attempt.tools.length} {attempt.tools.length === 1 ? "evento" : "eventos"} de
          herramientas · <code>{attempt.id}</code>
        </summary>
        {attempt.tools.length ? (
          <ol className="audit-steps">
            {attempt.tools.map((step) => (
              <Step key={step.event_id} step={step} />
            ))}
          </ol>
        ) : (
          <p className="audit-note">El asistente no usó herramientas.</p>
        )}
        {attempt.detail && <p className="audit-note">Evaluación: {attempt.detail}</p>}
      </details>
    </li>
  );
}

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
