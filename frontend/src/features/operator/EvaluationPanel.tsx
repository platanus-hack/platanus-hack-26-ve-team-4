import { type FormEvent, useState } from "react";
import type { Evaluation, Policy } from "./api";

export function EvaluationPanel({
  policies,
  evaluations,
  busy,
  start,
  stop,
  inspect,
}: {
  policies: Policy[];
  evaluations: Evaluation[];
  busy: boolean;
  start: (body: unknown) => void;
  stop: (id: string) => void;
  inspect: (id: string) => void;
}) {
  const [before, setBefore] = useState(0);
  const [after, setAfter] = useState<number | null>(null);
  const [repetitions, setRepetitions] = useState(1);
  const [maxCalls, setMaxCalls] = useState(1200);
  const target = after ?? policies.find((policy) => policy.status === "active")?.version ?? 0;
  const running = evaluations.some((evaluation) => evaluation.status === "running");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    start({ before_version: before, after_version: target, repetitions, max_calls: maxCalls });
  }
  return (
    <section>
      <h2>Evaluación comparativa</h2>
      <p className="muted">
        30 casos adversarios y 15 tareas legítimas por versión, en datos aislados y sin señuelo.
        Cada repetición compara 90 ejecuciones. En modo en vivo consume el presupuesto del
        proveedor.
      </p>
      <form onSubmit={submit} className="evaluation-form">
        <label htmlFor="before-version">Versión inicial</label>
        <select
          id="before-version"
          value={before}
          onChange={(event) => setBefore(Number(event.target.value))}
        >
          {policies.map((policy) => (
            <option key={policy.version} value={policy.version}>
              Política {policy.version}
            </option>
          ))}
        </select>
        <label htmlFor="after-version">Versión final</label>
        <select
          id="after-version"
          value={target}
          onChange={(event) => setAfter(Number(event.target.value))}
        >
          {policies.map((policy) => (
            <option key={policy.version} value={policy.version}>
              Política {policy.version}
            </option>
          ))}
        </select>
        <label htmlFor="eval-repetitions">Repeticiones por versión</label>
        <input
          id="eval-repetitions"
          type="number"
          min={1}
          max={3}
          value={repetitions}
          onChange={(event) => setRepetitions(Number(event.target.value))}
          required
        />
        <label htmlFor="eval-budget">Límite de llamadas al modelo</label>
        <input
          id="eval-budget"
          type="number"
          min={1}
          max={5000}
          value={maxCalls}
          onChange={(event) => setMaxCalls(Number(event.target.value))}
          required
        />
        <button type="submit" disabled={busy || running || before === target}>
          Comparar políticas · {repetitions * 90} ejecuciones
        </button>
      </form>
      {evaluations.map((evaluation) => (
        <article className="result" key={evaluation.id}>
          <h3>
            Política {evaluation.before_version} → {evaluation.after_version}
          </h3>
          <p>
            {evaluation.status} · {evaluation.completed}/{evaluation.total} ejecuciones ·{" "}
            {evaluation.repetitions} repeticiones
          </p>
          <progress
            max={Math.max(1, evaluation.total)}
            value={evaluation.completed}
            aria-label="Progreso de evaluación"
          />
          {Object.entries(evaluation.report.versions ?? {}).map(([version, result]) => (
            <div key={version} className="evaluation-metrics">
              <strong>Política {version}</strong>
              <p>
                Violaciones: {result.adversarial.confirmed_violations}/
                {result.adversarial.evaluable} adversarios evaluables ·{" "}
                {result.adversarial.inconclusive} inconclusos
              </p>
              <p>
                Utilidad: {result.legitimate.correct}/{result.legitimate.evaluable} tareas
                evaluables · {result.legitimate.inconclusive} inconclusas
              </p>
            </div>
          ))}
          {evaluation.report.limitations?.map((limitation) => (
            <p className="muted" key={limitation}>
              {limitation}
            </p>
          ))}
          <div className="controls">
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() => inspect(evaluation.id)}
            >
              Ver / descargar informe
            </button>
            {evaluation.status === "running" && (
              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() => stop(evaluation.id)}
              >
                Detener evaluación
              </button>
            )}
          </div>
        </article>
      ))}
    </section>
  );
}
