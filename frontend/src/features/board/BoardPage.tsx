import { type CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { errorMessage, isUnauthorized } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import { useArenaState } from "../arena/hooks/useArenaState";
import { InternalChatButton } from "../demo/InternalChatButton";
import { OperatorGate } from "../operator/OperatorGate";
import { loadBoard, setAccess } from "./api";
import { BoardHeader } from "./BoardHeader";
import { Carousel } from "./Carousel";
import { ChatTile } from "./ChatTile";
import { KpiColumn } from "./KpiColumn";
import { Scoreboard } from "./Scoreboard";
import { assignSlots, CHAT_COUNT, togglePin, VISIBLE } from "./slots";
import { carouselItem } from "./status";
import type { LiveSession } from "./types";
import { useStageScale } from "./useStageScale";
import "./stage.css";
import "./carousel.css";
import "./chat.css";
import "./kpi.css";
import "./scoreboard.css";

const POLL_MS = 1500;

export function BoardPage({
  onProjectingChange,
}: {
  onProjectingChange?: (projecting: boolean) => void;
} = {}) {
  return (
    <main className="page board-login">
      <h1>Arena en vivo</h1>
      <OperatorGate>
        {(secret, logout) => (
          <LiveArena
            key={secret}
            secret={secret}
            logout={logout}
            onProjectingChange={onProjectingChange}
          />
        )}
      </OperatorGate>
    </main>
  );
}

function LiveArena({
  secret,
  logout,
  onProjectingChange,
}: {
  secret: string;
  logout: (message?: string) => void;
  onProjectingChange?: (projecting: boolean) => void;
}) {
  const load = useCallback((signal: AbortSignal) => loadBoard(secret, signal), [secret]);
  const { data, error, refresh } = usePolling(load, POLL_MS);
  // Marcador: estado público de la ronda (sin secreto), con su propio sondeo.
  const arenaState = useArenaState();
  const scale = useStageScale();
  // Mientras la Arena está montada con el secreto se proyecta: la limpieza devuelve la barra (Salir o 401).
  useEffect(() => {
    onProjectingChange?.(true);
    return () => onProjectingChange?.(false);
  }, [onProjectingChange]);
  const [pins, setPins] = useState<string[]>([]);
  const [slots, setSlots] = useState<string[]>([]);
  const [announcement, setAnnouncement] = useState("");
  // Estado de acceso pedido al servidor: el botón queda bloqueado hasta que el tablero lo refleja.
  const [requested, setRequested] = useState<boolean | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const cache = useRef(new Map<string, LiveSession>());
  // Bloquea el doble clic: el estado llega tarde para el segundo clic.
  const inFlight = useRef(false);

  useEffect(() => {
    if (isUnauthorized(error))
      logout("La autorización no es válida o venció. Introduce el secreto de operador.");
  }, [error, logout]);

  useEffect(() => {
    if (requested === null) return;
    if (data?.accepting === requested) {
      inFlight.current = false;
      setRequested(null);
      return;
    }
    // Respaldo: si otra pantalla cambió el acceso, el botón no queda bloqueado para siempre.
    const timer = setTimeout(() => {
      inFlight.current = false;
      setRequested(null);
    }, 5000);
    return () => clearTimeout(timer);
  }, [data, requested]);

  const pinnedSet = useMemo(() => new Set(pins), [pins]);
  const known = useMemo(() => {
    const map = new Map<string, LiveSession>();
    for (const session of data?.sessions ?? []) {
      map.set(session.session_id, session);
      cache.current.set(session.session_id, session);
    }
    // Un chat fijado se queda aunque salga de las sesiones más recientes.
    for (const id of pinnedSet) {
      const old = cache.current.get(id);
      if (old && !map.has(id)) map.set(id, old);
    }
    return map;
  }, [data, pinnedSet]);
  useEffect(() => {
    setSlots((previous) => assignSlots(previous, known, pinnedSet, CHAT_COUNT));
  }, [known, pinnedSet]);

  const accepting = data?.accepting ?? true;
  const revealed = data?.revealed ?? false;
  const sessions = slots.flatMap((id) => known.get(id) ?? []);
  const items = sessions.map((session) => carouselItem(session, accepting, revealed));
  const total = sessions.length;
  const indexOf = new Map(sessions.map((session, n) => [session.session_id, n]));

  function pin(id: string) {
    const next = togglePin(pins, id);
    if (next.released) {
      const alias = cache.current.get(next.released)?.alias ?? next.released;
      setAnnouncement(`${alias} dejó de estar fijado (máximo 2 fijados)`);
    }
    setPins(next.order);
  }

  async function toggleAccess() {
    if (inFlight.current || !data) return;
    const open = !data.accepting;
    inFlight.current = true;
    setRequested(open);
    setActionError(null);
    try {
      await setAccess(secret, open);
      setAnnouncement(open ? "Acceso reabierto" : "Acceso cerrado");
      refresh();
    } catch (cause) {
      inFlight.current = false;
      setRequested(null);
      if (isUnauthorized(cause)) logout("La autorización no es válida o venció.");
      else setActionError(errorMessage(cause));
    }
  }

  const alert =
    actionError ??
    (error !== null && !isUnauthorized(error)
      ? `${errorMessage(error)}${data ? " Se conserva el último estado recibido." : ""}`
      : null);
  return (
    <div className="av-shell">
      <div className="av-stage" style={{ "--s": String(scale) } as CSSProperties}>
        <BoardHeader
          board={data}
          chats={total}
          visible={Math.min(VISIBLE, total)}
          busy={requested !== null}
          onToggleAccess={() => void toggleAccess()}
          onExit={() => logout()}
          launcher={<InternalChatButton secret={secret} />}
        />
        <div className="av-content">
          {data ? (
            <>
              <Carousel
                items={items}
                pinned={pins}
                scale={scale}
                renderChat={(id, inView) => {
                  const session = known.get(id);
                  if (!session) return null;
                  return (
                    <ChatTile
                      key={id}
                      session={session}
                      index={indexOf.get(id) ?? 0}
                      total={total}
                      pinned={pinnedSet.has(id)}
                      inView={inView}
                      accepting={accepting}
                      revealed={revealed}
                      now={data.generated_at}
                      onTogglePin={pin}
                    />
                  );
                }}
              />
              <div className="av-side">
                <KpiColumn kpis={data.kpis} sessionsTotal={data.sessions_total} />
                <Scoreboard arena={arenaState.data} />
              </div>
            </>
          ) : (
            <p className="av-waiting">Conectando con la arena…</p>
          )}
        </div>
        {alert && (
          <p className="av-alert" role="alert">
            {alert}
          </p>
        )}
      </div>
      <p className="av-sr" role="status" aria-live="polite">
        {announcement}
      </p>
    </div>
  );
}
