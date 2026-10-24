import type { TraceEvent } from "../types";
import { AttackGraph } from "./AttackGraph";
import type { LegitRow } from "./types";
import { useReplay, useReplayPhase } from "./useReplay";
import "./replay.css";

const LEGIT_LABELS: Record<string, string> = {
  "own-order": "Consulta de un pedido propio",
  "valid-refund": "Reembolso válido",
  knowledge: "Pregunta sobre envíos",
  preference: "Preferencia inocua",
  "security-mention": "Mención legítima de seguridad",
};

function LegitList({ rows, version }: { rows: LegitRow[]; version: number }) {
  return (
    <section className="replay-legit" aria-label="Tareas legítimas">
      <h3>Tareas legítimas con la política v{version}</h3>
      <ul>
        {rows.map((row) => (
          <li key={row.name} className={row.passed ? "replay-legit--ok" : "replay-legit--fail"}>
            <span aria-hidden="true">{row.passed ? "✓" : "✗"}</span>{" "}
            {LEGIT_LABELS[row.name] ?? "Tarea legítima"}:{" "}
            <strong>{row.passed ? "permitida" : "afectada"}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ReplayStage({ events }: { events: TraceEvent[] }) {
  const { replay } = useReplay(events);
  const phase = useReplayPhase(replay?.version);
  if (!replay) return null;
  const cut = phase >= 1;
  const sealed = phase >= 2;
  return (
    <section className="replay-stage" aria-label="Repetición del ataque">
      <h2>Repetición del ataque</h2>
      <p className="muted replay-source">
        Modo: {replay.source}. El «antes» se dibuja de la traza original y no se vuelve a ejecutar.
      </p>
      <div className="replay-columns">
        <article className="replay-side replay-side--before">
          <h3>Política v{replay.before.version}</h3>
          <p className="replay-caption replay-caption--effect">El efecto indebido ocurrió.</p>
          <AttackGraph graph={replay.before.graph} version={replay.before.version} cut={false} />
        </article>
        <article className="replay-side replay-side--after">
          <h3>Política v{replay.after.version}</h3>
          <p
            className={`replay-caption ${cut ? "replay-caption--blocked" : "replay-caption--wait"}`}
          >
            {cut ? "Arista cortada." : "Repitiendo las mismas llamadas…"}
          </p>
          <AttackGraph graph={replay.after.graph} version={replay.after.version} cut={cut} />
          {sealed && (
            <p className="replay-seal" role="status">
              bloqueado por política v{replay.after.version}
            </p>
          )}
        </article>
      </div>
      {sealed && <LegitList rows={replay.legit} version={replay.after.version} />}
    </section>
  );
}
