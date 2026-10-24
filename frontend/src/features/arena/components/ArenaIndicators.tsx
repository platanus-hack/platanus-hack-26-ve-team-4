import type { ArenaState } from "../types";

interface Indicator {
  label: string;
  value: string;
}

// Los cinco indicadores de docs/demo.md §5. Antes de revelar, la vista pública no separa
// violaciones confirmadas de éxitos en el señuelo: el servidor ya los entrega sumados.
function indicators(state: ArenaState): Indicator[] {
  return [
    { label: "Intentos terminados", value: `${state.finished}/${state.attempts_total}` },
    { label: "Éxitos aparentes · provisional", value: String(state.apparent_successes) },
    { label: "Intentos detenidos", value: String(state.prevented) },
    {
      label: "Hallazgos abiertos",
      value: state.findings_open === null ? "Sin datos" : String(state.findings_open),
    },
    { label: "Versión activa", value: `v${state.policy_version}` },
  ];
}

export function ArenaIndicators({ state, failed }: { state: ArenaState | null; failed: boolean }) {
  if (!state) {
    return (
      <p className="muted" role="status">
        {failed ? "No pudimos cargar los indicadores." : "Cargando indicadores…"}
      </p>
    );
  }
  return (
    <section aria-label="Indicadores de la ronda">
      <dl className="indicators">
        {indicators(state).map(({ label, value }) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="muted">
        {state.queued} en cola · {state.running} ejecutándose
        {failed && " · indicadores sin actualizar"}
      </p>
    </section>
  );
}
