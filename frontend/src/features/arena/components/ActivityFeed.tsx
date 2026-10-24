import { OUTCOME_LABELS, type PublicOutcome } from "../../../shared/attemptLabels";
import { StatusTag } from "../../../shared/ui/StatusTag";
import type { EventType, TraceEvent } from "../types";

const TITLES: Partial<Record<EventType, string>> = {
  attempt_queued: "Intento aceptado en la cola",
  attempt_started: "Intento en ejecución",
  attempt_evaluated: "Intento terminado",
  finding_opened: "Hallazgo confirmado",
  patch_proposed: "Parche propuesto",
  patch_validated: "Parche validado",
  policy_activated: "Política activada",
  policy_rolled_back: "Política revertida",
};

function outcomeOf(event: TraceEvent): PublicOutcome | null {
  const outcome = event.data.outcome;
  return typeof outcome === "string" && outcome in OUTCOME_LABELS
    ? (outcome as PublicOutcome)
    : null;
}

export function ActivityFeed({ events }: { events: TraceEvent[] }) {
  const shown = events.filter((event) => TITLES[event.type]).slice(0, 8);
  if (shown.length === 0) {
    return <p className="muted">Esperando actividad.</p>;
  }
  return (
    <ol className="timeline" aria-label="Actividad reciente">
      {shown.map((event) => {
        const outcome = outcomeOf(event);
        return (
          <li key={event.id}>
            <time dateTime={event.timestamp}>
              {new Date(event.timestamp).toLocaleTimeString("es")}
            </time>{" "}
            <strong>{TITLES[event.type]}</strong>
            {event.type === "policy_activated" && event.policy_version !== null && (
              <> · v{event.policy_version}</>
            )}{" "}
            {outcome && (
              <StatusTag text={OUTCOME_LABELS[outcome].text} tone={OUTCOME_LABELS[outcome].tone} />
            )}
          </li>
        );
      })}
    </ol>
  );
}
