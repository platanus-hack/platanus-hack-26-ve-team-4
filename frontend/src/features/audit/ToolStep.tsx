import { ARMOR, STEPS } from "./labels";
import type { ToolStep } from "./types";

function json(value: Record<string, unknown>): string {
  return Object.keys(value).length ? JSON.stringify(value, null, 2) : "—";
}

function armorNote(step: ToolStep): string | null {
  if (step.kind !== "tool_denied" || !step.reason) return null;
  const reason = ARMOR[step.reason] ?? `Motivo: ${step.reason}`;
  const stage = step.stage ? ` · etapa ${step.stage}` : "";
  const detail = step.detail ? ` — ${step.detail}` : "";
  return `${reason}${stage}${detail}`;
}

export function ToolStepItem({ step }: { step: ToolStep }) {
  const kind = STEPS[step.kind] ?? { label: step.kind, tone: "muted" };
  const effect = typeof step.effect.kind === "string" ? step.effect.kind : null;
  const armor = armorNote(step);
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
      {armor && <p className="audit-note audit-armor">{armor}</p>}
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
