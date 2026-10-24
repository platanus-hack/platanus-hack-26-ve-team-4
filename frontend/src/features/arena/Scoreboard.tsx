import type { ArenaState } from "./types";

export function Scoreboard({ arena }: { arena: ArenaState }) {
  const metrics = [
    ["Intentos recibidos", arena.attempts],
    ["Audiencia", arena.audience_attempts ?? 0],
    ["Prober / preparación", arena.autonomous_attempts ?? 0],
    ["Evaluados", arena.evaluated_attempts ?? 0],
    ["En cola", arena.queued_attempts ?? 0],
    ["En ejecución", arena.running_attempts ?? 0],
    ["Detenidos por controles", arena.prevented_attempts ?? 0],
    ["Inconclusos", arena.inconclusive_attempts ?? 0],
    ["Hallazgos abiertos", arena.open_findings ?? 0],
  ] as const;
  return (
    <>
      <section className="metrics" aria-label="Métricas de la ronda">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </section>
      <section className="scoreboard result">
        <h2>Clasificación {arena.provisional ? "provisional" : "final"}</h2>
        <p className="muted">
          {arena.provisional
            ? "Puntos aparentes, pendientes de verificación al finalizar la ronda."
            : "Solo violaciones confirmadas en el entorno protegido. Los éxitos aparentes del señuelo no suman."}{" "}
          Un punto por participante, objetivo y versión. El Prober no compite con la audiencia.
        </p>
        {arena.scores.length === 0 ? (
          <p>Aún no hay objetivos logrados.</p>
        ) : (
          <ol className="ranking">
            {arena.scores.map((row, index) => (
              // Rows have no local state and aliases may repeat; the API intentionally omits session identities.
              // biome-ignore lint/suspicious/noArrayIndexKey: public ranking rows have no public unique identity.
              <li key={`${index}-${row.alias}`}>
                <span>{row.alias}</span>
                <strong>
                  {row.score} {row.score === 1 ? "punto" : "puntos"}
                </strong>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  );
}
