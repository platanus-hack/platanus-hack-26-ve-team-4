import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { errorMessage, isUnauthorized } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import { OperatorGate } from "../operator/OperatorGate";
import { loadBoard, SLOT_COUNT } from "./api";
import "./board.css";
import { ChatTile } from "./ChatTile";
import { KpiColumn } from "./KpiColumn";
import { assignSlots } from "./slots";
import type { LiveSession } from "./types";

const POLL_MS = 1500;

export function BoardPage() {
  return (
    <main className="board-shell">
      <h1 className="visually-hidden">Tablero de ataque en vivo</h1>
      <OperatorGate>
        {(secret, logout) => <Board key={secret} secret={secret} logout={logout} />}
      </OperatorGate>
    </main>
  );
}

function Board({ secret, logout }: { secret: string; logout: (message?: string) => void }) {
  const load = useCallback((signal: AbortSignal) => loadBoard(secret, signal), [secret]);
  const { data, error } = usePolling(load, POLL_MS);
  const [pinned, setPinned] = useState<ReadonlySet<string>>(new Set());
  const [slots, setSlots] = useState<string[]>([]);
  const cache = useRef(new Map<string, LiveSession>());
  useEffect(() => {
    if (isUnauthorized(error))
      logout("La autorización no es válida o venció. Introduce el secreto de operador.");
  }, [error, logout]);

  const known = useMemo(() => {
    const map = new Map<string, LiveSession>();
    for (const session of data?.sessions ?? []) {
      map.set(session.session_id, session);
      cache.current.set(session.session_id, session);
    }
    // Una sesión fijada se queda en su casilla aunque salga de las más recientes.
    for (const id of pinned) {
      const old = cache.current.get(id);
      if (old && !map.has(id)) map.set(id, old);
    }
    return map;
  }, [data, pinned]);
  useEffect(() => {
    setSlots((previous) => assignSlots(previous, known, pinned, SLOT_COUNT));
  }, [known, pinned]);

  function togglePin(id: string) {
    setPinned((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }

  return (
    <div className="board">
      <header className="board-header">
        <p className="eyebrow">Agent Zero · Visión de ataque</p>
        <p role="status" className="board-status">
          {data === null
            ? "Conectando…"
            : data.revealed
              ? "Ronda revelada: se muestran rutas y violaciones de todos."
              : "Antes de revelar: el público no muestra ruta ni violaciones."}
          {data && data.llm_mode === "demo" && " · Modelo simulado"}
        </p>
        <button type="button" className="secondary" onClick={() => logout()}>
          Cerrar acceso
        </button>
      </header>
      {error !== null && !isUnauthorized(error) && (
        <p role="alert" className="board-alert">
          {errorMessage(error)} {data ? "Se conserva el último estado recibido." : ""}
        </p>
      )}
      <div className="board-body">
        <section className="tiles" aria-label="Chats de atacantes">
          {Array.from({ length: SLOT_COUNT }, (_, index) => {
            const id = slots[index];
            const session = id ? (known.get(id) ?? null) : null;
            return (
              <ChatTile
                key={id ?? `libre-${index}`}
                session={session}
                pinned={id !== undefined && pinned.has(id)}
                onTogglePin={togglePin}
              />
            );
          })}
        </section>
        {data ? (
          <KpiColumn kpis={data.kpis} />
        ) : (
          <aside className="kpis" aria-label="Analíticas">
            <p className="muted">Cargando analíticas…</p>
          </aside>
        )}
      </div>
    </div>
  );
}
