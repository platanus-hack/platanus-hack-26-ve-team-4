import { useState } from "react";
import { AttackGraph } from "../arena/replay/AttackGraph";
import type { Replay, ReplayGraph } from "../arena/replay/types";
import { useReplayPhase } from "../arena/replay/useReplay";
import type { MonitorAttempt } from "./types";

const LEGIT_LABELS: Record<string, string> = {
  "own-order": "Pedido propio",
  "valid-refund": "Reembolso válido",
  knowledge: "Pregunta de envíos",
  preference: "Preferencia inocua",
  "security-mention": "Mención legítima de seguridad",
};

function caption(attempt: MonitorAttempt, graph: ReplayGraph): [string, string] {
  if (attempt.route === "honeypot")
    return ["Aislado en el señuelo: nada llegó al entorno real.", "decoy"];
  if (attempt.outcome === "confirmed_violation") return ["El efecto indebido ocurrió.", "effect"];
  if (graph.edges.some((edge) => edge.state === "blocked"))
    return [`Bloqueado por la política v${attempt.policy_version}.`, "blocked"];
  if (attempt.outcome === "inconclusive")
    return ["Traza sin veredicto: no cuenta como defensa.", "wait"];
  if (attempt.outcome === null) return ["El intento sigue en curso.", "wait"];
  return ["Sin efecto indebido.", "blocked"];
}

function Split({ replay }: { replay: Replay }) {
  const phase = useReplayPhase(replay.version);
  const cut = phase >= 1;
  return (
    <div className="replay-columns">
      <article className="replay-side">
        <h3>Política v{replay.before.version}</h3>
        <p className="replay-caption replay-caption--effect">El efecto indebido ocurrió.</p>
        <AttackGraph graph={replay.before.graph} version={replay.before.version} cut={false} />
      </article>
      <article className="replay-side">
        <h3>Política v{replay.after.version}</h3>
        <p className={`replay-caption ${cut ? "replay-caption--blocked" : "replay-caption--wait"}`}>
          {cut ? "Arista cortada." : "Repitiendo las mismas llamadas…"}
        </p>
        <AttackGraph graph={replay.after.graph} version={replay.after.version} cut={cut} />
        {phase >= 2 && (
          <>
            <p className="replay-seal" role="status">
              bloqueado por política v{replay.after.version}
            </p>
            <ul className="monitor-legit" aria-label="Tareas legítimas">
              {replay.legit.map((row) => (
                <li key={row.name} className={row.passed ? "is-ok" : "is-fail"}>
                  {LEGIT_LABELS[row.name] ?? "Tarea legítima"}
                </li>
              ))}
            </ul>
          </>
        )}
      </article>
    </div>
  );
}

export function AttemptReplay({
  attempt,
  graph,
  replay,
}: {
  attempt: MonitorAttempt;
  graph: ReplayGraph;
  replay: Replay | null;
}) {
  const [run, setRun] = useState(0);
  if (replay) {
    return (
      <div className="monitor-replay">
        <div className="monitor-row">
          <span className="monitor-label">Repetición en pantalla dividida · {replay.source}</span>
          <button type="button" className="monitor-chip" onClick={() => setRun((n) => n + 1)}>
            Repetir animación
          </button>
        </div>
        <Split key={run} replay={replay} />
      </div>
    );
  }
  const [text, tone] = caption(attempt, graph);
  const empty = graph.nodes.length <= 1;
  return (
    <div className={`monitor-replay ${attempt.route === "honeypot" ? "is-decoy" : ""}`}>
      <span className="monitor-label">Llamadas a herramientas de la interacción</span>
      <article className="replay-side">
        <h3>{attempt.route === "honeypot" ? "Señuelo" : `Política v${attempt.policy_version}`}</h3>
        <p className={`replay-caption replay-caption--${tone}`}>{text}</p>
        {empty ? (
          <p className="muted monitor-small">El agente respondió sin llamar herramientas.</p>
        ) : (
          <AttackGraph graph={graph} version={attempt.policy_version} cut />
        )}
        {attempt.outcome === "confirmed_violation" && !attempt.patch && (
          <p className="muted monitor-small">Parche en análisis o pendiente de validación.</p>
        )}
      </article>
    </div>
  );
}
