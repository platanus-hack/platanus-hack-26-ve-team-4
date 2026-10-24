import { useEffect, useState } from "react";
import { requestJson } from "../../shared/api/http";

interface ArenaState {
  accepting: boolean;
  provisional: boolean;
  policy_version: number;
  attempts: number;
  scores: { alias: string; score: number }[];
}

export function Scoreboard() {
  const [arena, setArena] = useState<ArenaState | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const load = () =>
      requestJson<ArenaState>("/api/arena/state", { signal: controller.signal })
        .then((state) => {
          if (!controller.signal.aborted) setArena(state);
        })
        .catch(() => {});
    void load();
    const timer = setInterval(load, 1500);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, []);
  if (!arena) return <p>Cargando clasificación…</p>;
  return (
    <section>
      <p>
        Política activa: {arena.policy_version} · {arena.attempts} intentos ·{" "}
        {arena.accepting ? "Entradas abiertas" : "Entradas cerradas"}
      </p>
      <h2>Clasificación {arena.provisional ? "provisional" : "final"}</h2>
      {arena.scores.length === 0 ? (
        <p>Aún no hay objetivos logrados.</p>
      ) : (
        <ol>
          {arena.scores.map((row) => (
            <li key={row.alias}>
              {row.alias}: {row.score}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
