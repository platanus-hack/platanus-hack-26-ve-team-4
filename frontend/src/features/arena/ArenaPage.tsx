import { useEffect, useState } from "react";
import { errorMessage } from "../../shared/api/http";
import { useArenaEvents } from "./hooks/useArenaEvents";
import { useArenaState } from "./hooks/useArenaState";
import { JoinCode } from "./JoinCode";
import { ModeNotice } from "./ModeNotice";
import { ReplayStage } from "./replay/ReplayStage";
import { Scoreboard } from "./Scoreboard";
import type { EventType } from "./types";

const CONNECTION_LABELS = {
  connecting: "Conectando…",
  open: "Eventos en vivo",
  reconnecting: "Reconectando eventos…",
} as const;
const EVENT_LABELS: Record<EventType, string> = {
  attempt_queued: "Nuevo intento en cola",
  attempt_started: "Asistente trabajando",
  attempt_completed: "Respuesta completada",
  tool_proposed: "Herramienta propuesta",
  tool_denied: "Control de herramienta aplicado",
  tool_completed: "Herramienta completada",
  route_changed: "Ruta actualizada",
  attempt_evaluated: "Intento evaluado",
  finding_opened: "Hallazgo confirmado",
  patch_proposed: "Control candidato propuesto",
  patch_validated: "Validación de control completada",
  policy_activated: "Nueva política activada",
  policy_rolled_back: "Política revertida",
};
function elapsed(start: string | undefined, now: number) {
  const total = start ? Math.max(0, Math.floor((now - Date.parse(start)) / 1000)) : 0;
  return Number.isFinite(total)
    ? `${Math.floor(total / 60)
        .toString()
        .padStart(2, "0")}:${(total % 60).toString().padStart(2, "0")}`
    : "—";
}

export function ArenaPage() {
  const arena = useArenaState();
  const { events, connection } = useArenaEvents("/api/arena/events", 100, arena.data?.round_id);
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return (
    <main className="page arena-page">
      <header className="arena-header">
        <div>
          <p className="eyebrow">Agent Zero · Arena en vivo</p>
          <h1>Cada ataque deja evidencia.</h1>
        </div>
        <span className="status" role="status">
          {CONNECTION_LABELS[connection]}
        </span>
      </header>
      {Boolean(arena.error) && (
        <p role="alert">
          {errorMessage(arena.error)}{" "}
          {arena.data ? "Se muestran los últimos datos recibidos." : "Esperando datos de la ronda."}
        </p>
      )}
      {arena.data ? (
        <>
          <ModeNotice arena={arena.data} />
          <div className="round-banner">
            <strong>
              {arena.data.accepting
                ? "Entradas abiertas"
                : arena.data.revealed
                  ? "Ronda revelada"
                  : "Entradas pausadas"}
            </strong>
            <span>Política {arena.data.policy_version}</span>
            <span>
              {arena.data.session_count ?? 0}/{arena.data.session_limit ?? "—"} participantes
            </span>
            <span>
              Tiempo de ronda <time>{elapsed(arena.data.started_at, now)}</time>
            </span>
          </div>
          <JoinCode />
          <Scoreboard arena={arena.data} />
        </>
      ) : (
        !arena.error && <p role="status">Cargando ronda…</p>
      )}
      <ReplayStage events={events} />
      <section>
        <h2>Actividad reciente</h2>
        <p className="muted">
          Eventos de esta conexión. Los contadores y la clasificación proceden del registro completo
          del servidor.
        </p>
        {events.length === 0 ? (
          <p>Esperando actividad.</p>
        ) : (
          <ol className="timeline">
            {events.map((event) => (
              <li key={event.id}>
                <time dateTime={event.timestamp}>
                  {new Date(event.timestamp).toLocaleTimeString("es")}
                </time>
                <span>{EVENT_LABELS[event.type]}</span>
                {event.policy_version !== null && (
                  <span className="muted">v{event.policy_version}</span>
                )}
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  );
}
