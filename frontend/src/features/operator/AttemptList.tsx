import { useState } from "react";
import type { OperatorAttempt } from "./api";

interface Props {
  attempts: OperatorAttempt[];
  disabled: boolean;
  inspect: (id: string) => void;
  replay: (id: string) => void;
}
export const OUTCOMES: Record<string, string> = {
  apparent_success: "Éxito aparente",
  confirmed_violation: "Violación confirmada",
  contained_honeypot: "Contenido en señuelo",
  prevented: "Detenido",
  not_achieved: "Objetivo no logrado",
  inconclusive: "Inconcluso",
  queued: "En cola",
  running: "Ejecutándose",
  evaluated: "Evaluado",
};
export function AttemptList({ attempts, disabled, inspect, replay }: Props) {
  const [filter, setFilter] = useState("all");
  const filtered = attempts.filter((attempt) => filter === "all" || attempt.origin === filter);
  return (
    <section>
      <div className="section-heading">
        <h2>Intentos · {attempts.length}</h2>
        <label>
          Origen{" "}
          <select value={filter} onChange={(event) => setFilter(event.target.value)}>
            <option value="all">Todos</option>
            <option value="audience">Audiencia</option>
            <option value="autonomous">Prober / preparación</option>
          </select>
        </label>
      </div>
      {!filtered.length && <p>Aún no hay intentos para este origen.</p>}
      {filtered
        .slice(-50)
        .reverse()
        .map((attempt) => (
          <article className="result" key={attempt.id}>
            <p>
              <strong>{OUTCOMES[attempt.outcome ?? attempt.status] ?? attempt.status}</strong> ·
              política {attempt.policy_version} ·{" "}
              {attempt.route === "honeypot" ? "Señuelo aislado" : "Entorno protegido"} ·{" "}
              {attempt.origin === "audience" ? "Audiencia" : "Autónomo"}
            </p>
            <code>{attempt.id}</code>
            {attempt.messages?.[0] && <p className="reply">{attempt.messages[0]}</p>}
            <div className="controls">
              <button
                className="secondary"
                type="button"
                disabled={disabled}
                onClick={() => inspect(attempt.id)}
              >
                Ver evidencia
              </button>
              <button
                className="secondary"
                type="button"
                disabled={disabled || !["evaluated", "inconclusive"].includes(attempt.status)}
                onClick={() => replay(attempt.id)}
              >
                Repetir en sesión limpia
              </button>
            </div>
          </article>
        ))}
      {filtered.length > 50 && (
        <p className="muted">
          Se muestran los últimos 50. El servidor conserva la evidencia completa.
        </p>
      )}
    </section>
  );
}
