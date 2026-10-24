import { useEffect, useState } from "react";
import { getJson } from "../../../shared/api/http";
import type { ArenaState } from "../types";

const REFRESH_DELAY_MS = 300;

/** Carga los contadores al abrir la pantalla y los vuelve a pedir tras cada evento en vivo. */
export function useArenaState(lastEventId: number | null) {
  const [state, setState] = useState<ArenaState | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    // `lastEventId` solo dispara la recarga; varios eventos seguidos se agrupan en una.
    void lastEventId;
    let cancelled = false;
    const timer = setTimeout(() => {
      getJson<ArenaState>("/api/arena/state")
        .then((next) => {
          if (!cancelled) {
            setState(next);
            setFailed(false);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setFailed(true);
          }
        });
    }, REFRESH_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [lastEventId]);

  return { state, failed };
}
