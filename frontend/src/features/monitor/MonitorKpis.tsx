import { NUMBER, patchDelay, usd } from "./labels";
import type { Monitor, Outcome } from "./types";

function patchRange(monitor: Monitor): string {
  const delays = monitor.attempts
    .map(patchDelay)
    .filter((value): value is number => value !== null);
  if (!delays.length) return "—";
  const low = Math.min(...delays);
  const high = Math.max(...delays);
  return low === high ? `${low} s` : `${low}–${high} s`;
}

export function MonitorKpis({ monitor }: { monitor: Monitor }) {
  const count = (outcome: Outcome) =>
    monitor.attempts.filter((attempt) => attempt.outcome === outcome).length;
  const { totals } = monitor;
  const measured = totals.measured_calls > 0;
  const kpis: [string, string, string][] = [
    [NUMBER.format(monitor.attempts.length), "Intentos", "line"],
    [NUMBER.format(count("confirmed_violation")), "Violaciones confirmadas", "danger"],
    [NUMBER.format(count("prevented")), "Impedidos por política", "accent"],
    [NUMBER.format(count("contained_honeypot")), "Contenidos en señuelo", "decoy"],
    [NUMBER.format(count("not_achieved")), "No logrados", "muted"],
    [NUMBER.format(count("inconclusive")), "Inconclusos", "warn"],
    [patchRange(monitor), "Tiempo de parcheo", "accent"],
    [
      measured ? usd(totals.cost_usd) : "simulado",
      `Coste · ${NUMBER.format(totals.calls)} llamadas`,
      "line",
    ],
  ];
  return (
    <section className="monitor-kpis" aria-label="Resumen de la ronda">
      {kpis.map(([value, label, tone]) => (
        <div key={label} className={`monitor-kpi tone-${tone}`}>
          <b>{value}</b>
          <span>{label}</span>
        </div>
      ))}
    </section>
  );
}
