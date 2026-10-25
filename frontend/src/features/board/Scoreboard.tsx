import type { ArenaState, ScoreRow } from "../arena/types";

/** Filas del marcador: el top 3 cabe en el panel de 145 px. */
const TOP = 3;

function points(count: number) {
  return `${count} ${count === 1 ? "punto" : "puntos"}`;
}

/** Tras revelar: cuántos puntos parecían reales, cuántos se confirmaron y cuántos quedaron en el señuelo. */
function reconciliation(row: ScoreRow) {
  if (row.apparent === undefined) return null;
  return (
    <small>
      {row.apparent} aparentes · {row.score} confirmados · {row.contained ?? 0} en el señuelo
    </small>
  );
}

/**
 * Marcador en vivo (440 × 145): antes de revelar, puntos provisionales con los aparentes
 * (incluidos los del señuelo); tras revelar, la reconciliación por fila. Las cifras vienen de
 * GET /api/arena/state y no se calculan aquí.
 */
export function Scoreboard({ arena }: { arena: ArenaState | null }) {
  if (arena === null) {
    return (
      <aside className="av-score" aria-label="Marcador">
        <p className="av-score-empty">Marcador no disponible</p>
      </aside>
    );
  }
  // Un estado incompleto no debe tumbar el tablero: sin filas se muestra el aviso de abajo.
  const rows = (arena.scores ?? []).slice(0, TOP);
  return (
    <aside className="av-score" aria-label="Marcador">
      <header className="av-score-head">
        <h2>{arena.revealed ? "Marcador final" : "Marcador provisional"}</h2>
        {!arena.revealed && <span className="av-score-flag">provisional</span>}
      </header>
      {!arena.revealed && (
        <p className="av-score-note">
          Puntos aparentes: incluyen intentos contenidos en el señuelo
        </p>
      )}
      <dl className="av-score-counts">
        <div>
          <dt>Violaciones confirmadas</dt>
          <dd>{arena.confirmed_violations ?? 0}</dd>
        </div>
        <div>
          <dt>Contenidos en el señuelo</dt>
          <dd>{arena.contained_honeypot ?? 0}</dd>
        </div>
      </dl>
      {rows.length === 0 ? (
        <p className="av-score-empty">Aún no hay objetivos logrados.</p>
      ) : (
        <ol className="av-score-rank">
          {rows.map((row, index) => (
            // Rows have no local state and aliases may repeat; the API intentionally omits session identities.
            // biome-ignore lint/suspicious/noArrayIndexKey: public ranking rows have no public unique identity.
            <li key={`${index}-${row.alias}`}>
              <span className="alias">{row.alias}</span>
              <strong>{points(row.score)}</strong>
              {arena.revealed && reconciliation(row)}
            </li>
          ))}
        </ol>
      )}
    </aside>
  );
}
