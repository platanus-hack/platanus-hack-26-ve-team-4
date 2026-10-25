import { OUTCOMES } from "../monitor/labels";
import { familyLabel, moment, OBJECTIVES, STATUSES, seconds } from "./labels";
import { ToolStepItem } from "./ToolStep";
import type { AuditAttempt } from "./types";

function deniedValidators(attempt: AuditAttempt): string[] {
  const names = attempt.tools
    .filter((step) => step.kind === "tool_denied" && step.validator)
    .map((step) => step.validator);
  return [...new Set(names)];
}

function Classification({ attempt }: { attempt: AuditAttempt }) {
  const status = STATUSES[attempt.status] ?? { label: attempt.status, tone: "muted" };
  const route = attempt.route === "honeypot" ? "señuelo" : "protegida";
  return (
    <section className="audit-class" aria-label="Clasificación">
      <span className={`monitor-pill tone-${status.tone}`}>{status.label}</span>
      <span className="monitor-pill tone-muted">Familia: {familyLabel(attempt.family)}</span>
      <span className="monitor-pill tone-muted">Ruta: {route}</span>
      {deniedValidators(attempt).map((validator) => (
        <span key={validator} className="monitor-pill tone-accent">
          Negado por {validator}
        </span>
      ))}
    </section>
  );
}

export function Exchange({ attempt, live = false }: { attempt: AuditAttempt; live?: boolean }) {
  const outcome = OUTCOMES[attempt.outcome ?? "pending"];
  const violated = attempt.verdicts.filter((verdict) => verdict.violated);
  const waiting =
    live && !attempt.reply && (attempt.status === "queued" || attempt.status === "running");
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
      {live && <Classification attempt={attempt} />}
      {attempt.messages.map((message, index) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: los turnos no tienen otro identificador.
        <p key={index} className="bubble bubble--user">
          <span className="visually-hidden">Participante: </span>
          {message}
        </p>
      ))}
      {attempt.reply ? (
        <p className="bubble bubble--bot">
          <span className="visually-hidden">Yummi: </span>
          {attempt.reply}
        </p>
      ) : (
        <p className="audit-note">
          {waiting ? "Esperando respuesta…" : `Sin respuesta (${attempt.status}).`}
        </p>
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
      <details className="audit-trace" open={live || undefined}>
        <summary>
          Traza · {attempt.tools.length} {attempt.tools.length === 1 ? "evento" : "eventos"} de
          herramientas · <code>{attempt.id}</code>
        </summary>
        {attempt.tools.length ? (
          <ol className="audit-steps">
            {attempt.tools.map((step) => (
              <ToolStepItem key={step.event_id} step={step} />
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
