import { useEffect, useState } from "react";

export const ROUND_MS = 210_000;

function clock(ms: number): string {
  const seconds = Math.ceil(ms / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

/** Cronómetro local de la presentación: no abre ni cierra entradas en el servidor. */
export function RoundTimer({ durationMs = ROUND_MS }: { durationMs?: number }) {
  const [elapsed, setElapsed] = useState(0);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (startedAt === null) {
      return;
    }
    const timer = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(timer);
  }, [startedAt]);

  const used = elapsed + (startedAt === null ? 0 : now - startedAt);
  const remaining = Math.max(0, durationMs - used);

  useEffect(() => {
    if (startedAt !== null && remaining === 0) {
      setElapsed(durationMs);
      setStartedAt(null);
    }
  }, [remaining, startedAt, durationMs]);

  function toggle() {
    if (startedAt === null) {
      const start = Date.now();
      setNow(start);
      setStartedAt(start);
    } else {
      setElapsed(used);
      setStartedAt(null);
    }
  }

  return (
    <section className="timer" aria-labelledby="timer-title">
      <h2 id="timer-title">Tiempo de la ronda</h2>
      <p className="clock" role="timer">
        {clock(remaining)}
      </p>
      <div className="row">
        <button type="button" className="secondary" onClick={toggle} disabled={remaining === 0}>
          {startedAt === null ? "Iniciar" : "Pausar"}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => {
            setElapsed(0);
            setStartedAt(null);
          }}
        >
          Reiniciar
        </button>
      </div>
    </section>
  );
}
