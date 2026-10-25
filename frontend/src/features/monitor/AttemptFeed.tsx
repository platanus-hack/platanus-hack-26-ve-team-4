import { clock, familyOf, ORIGINS, outcomeOf } from "./labels";
import type { MonitorAttempt, Outcome } from "./types";

export type Filter = "all" | Outcome;

const FILTERS: [Filter, string][] = [
  ["all", "Todos"],
  ["confirmed_violation", "Violaciones"],
  ["prevented", "Impedidos"],
  ["contained_honeypot", "Señuelo"],
  ["inconclusive", "Inconclusos"],
];

export function AttemptFeed({
  attempts,
  filter,
  onFilter,
  selected,
  onSelect,
}: {
  attempts: MonitorAttempt[];
  filter: Filter;
  onFilter: (filter: Filter) => void;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  // Lo más reciente arriba: es lo que la empresa mira durante la ronda.
  const list = attempts
    .filter((attempt) => filter === "all" || attempt.outcome === filter)
    .slice()
    .reverse();
  return (
    <aside className="monitor-panel" aria-label="Interacciones">
      <div className="monitor-row">
        <h2>Interacciones</h2>
        <span className="monitor-label">
          {list.length} de {attempts.length}
        </span>
      </div>
      <fieldset className="monitor-filters" aria-label="Filtrar interacciones">
        {FILTERS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className="monitor-chip"
            aria-pressed={filter === key}
            onClick={() => onFilter(key)}
          >
            {label}
          </button>
        ))}
      </fieldset>
      <div className="monitor-feed">
        {list.map((attempt) => {
          const outcome = outcomeOf(attempt);
          return (
            <button
              key={attempt.id}
              type="button"
              className={`monitor-item tone-${outcome.tone}`}
              aria-current={attempt.id === selected}
              onClick={() => onSelect(attempt.id)}
            >
              <span className="monitor-item-top">
                <span className="monitor-item-time">{clock(attempt.created_at)}</span>
                <span className="monitor-item-origin">
                  {ORIGINS[attempt.origin] ?? attempt.origin} · v{attempt.policy_version}
                </span>
                <span className="monitor-item-id">{attempt.id.slice(-6)}</span>
              </span>
              <span className="monitor-item-msg">{attempt.messages[0] ?? "(sin texto)"}</span>
              <span className="monitor-item-foot">
                <span className="monitor-pill">{outcome.label}</span>
                <span className="monitor-item-family">{familyOf(attempt)}</span>
              </span>
            </button>
          );
        })}
        {!list.length && <p className="muted monitor-small">Sin interacciones con este filtro.</p>}
      </div>
    </aside>
  );
}
