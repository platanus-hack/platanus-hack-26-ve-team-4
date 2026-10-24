import { CoevolutionPlot } from "./CoevolutionPlot";
import { useCoevolution } from "./hooks/useCoevolution";
import type { CoevolutionResponse, CoevolutionRound } from "./types";

function breakText(round: CoevolutionRound, budget: number) {
  return round.queries_to_break !== null
    ? `se rompió en la consulta ${round.queries_to_break}`
    : `≥ ${Math.max(round.queries, budget)} consultas sin romper`;
}

function Counter({ data }: { data: CoevolutionResponse }) {
  const summary = data.summary;
  if (!summary || summary.baseline.version === summary.latest.version) return null;
  return (
    <p className="coevo-counter">
      Consultas para romper v{summary.baseline.version}: {breakText(summary.baseline, data.budget)}.
      v{summary.latest.version}: {breakText(summary.latest, data.budget)}.
    </p>
  );
}

function RoundsTable({ rounds, budget }: { rounds: CoevolutionRound[]; budget: number }) {
  return (
    <table className="coevo-table">
      <caption className="muted">Datos de la curva (presupuesto: {budget} por versión)</caption>
      <thead>
        <tr>
          <th>Versión</th>
          <th>Consultas</th>
          <th>Violaciones</th>
          <th>Tasa</th>
          <th>Primera ruptura</th>
        </tr>
      </thead>
      <tbody>
        {rounds.map((round) => (
          <tr key={round.version}>
            <td>v{round.version}</td>
            <td>{round.queries}</td>
            <td>
              {round.violations}/{round.evaluable}
            </td>
            <td>
              {round.success_rate === null ? "—" : `${Math.round(round.success_rate * 100)}%`}
            </td>
            <td>
              {round.first_break
                ? `${round.first_break.mutator} · ${round.first_break.family ?? "—"}`
                : "sin ruptura"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function CoevolutionChart() {
  const { data } = useCoevolution();
  const rounds = Array.isArray(data?.versions) ? data.versions : [];
  return (
    <section className="coevolution" aria-label="Curva de co-evolución del Prober">
      <h2>Prober adaptativo frente a cada política</h2>
      {rounds.length === 0 || !data ? (
        <p className="muted">
          Sin campaña adaptativa todavía. Se lanza desde Operación con generación adaptativa.
        </p>
      ) : (
        <>
          <CoevolutionPlot rounds={rounds} />
          <Counter data={data} />
          <RoundsTable rounds={rounds} budget={data.budget} />
        </>
      )}
      <p className="muted">
        Robustez frente a este Prober y este presupuesto, no general.
        {data?.evidence_mode === "simulated" &&
          " Evidencia simulada: la víctima es un intérprete de reglas, no un modelo real."}
      </p>
    </section>
  );
}
