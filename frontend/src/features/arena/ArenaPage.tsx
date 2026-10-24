import { useArenaEvents } from "./hooks/useArenaEvents";

const CONNECTION_LABELS = {
  connecting: "Conectando…",
  open: "En vivo",
  reconnecting: "Reconectando…",
} as const;

export function ArenaPage() {
  const { events, connection } = useArenaEvents();

  return (
    <main className="page">
      <header className="arena-header">
        <h1>Arena</h1>
        <span className="status">{CONNECTION_LABELS[connection]}</span>
      </header>
      {events.length === 0 ? (
        <p>Esperando actividad.</p>
      ) : (
        <ol className="timeline">
          {events.map((event) => (
            <li key={event.id}>
              <time dateTime={event.timestamp}>
                {new Date(event.timestamp).toLocaleTimeString("es")}
              </time>{" "}
              {event.type}
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
