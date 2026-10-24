import { ActivityFeed } from "./components/ActivityFeed";
import { ArenaIndicators } from "./components/ArenaIndicators";
import { JoinQr } from "./components/JoinQr";
import { RoundTimer } from "./components/RoundTimer";
import { useArenaEvents } from "./hooks/useArenaEvents";
import { useArenaState } from "./hooks/useArenaState";

const CONNECTION_LABELS = {
  connecting: "Conectando…",
  open: "En vivo",
  reconnecting: "Reconectando…",
} as const;

export function ArenaPage() {
  const { events, connection } = useArenaEvents();
  const { state, failed } = useArenaState(events[0]?.id ?? null);

  return (
    <main className="page arena">
      <header className="arena-header">
        <h1>Arena</h1>
        <span className="status" role="status">
          {CONNECTION_LABELS[connection]}
        </span>
      </header>
      <div className="arena-grid">
        <JoinQr />
        <div className="arena-main">
          <RoundTimer />
          <ArenaIndicators state={state} failed={failed} />
          <h2>Actividad reciente</h2>
          <ActivityFeed events={events} />
        </div>
      </div>
      <p className="muted">
        Los resultados son provisionales hasta la revelación. El cronómetro es local y no cierra
        entradas.
      </p>
    </main>
  );
}
