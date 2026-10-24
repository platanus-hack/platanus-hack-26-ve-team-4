import { useCallback } from "react";
import { requestJson } from "../../../shared/api/http";
import { usePolling } from "../../../shared/api/usePolling";
import type { ArenaState } from "../types";

export function useArenaState() {
  const load = useCallback(
    (signal: AbortSignal) => requestJson<ArenaState>("/api/arena/state", { signal }),
    [],
  );
  return usePolling(load);
}
