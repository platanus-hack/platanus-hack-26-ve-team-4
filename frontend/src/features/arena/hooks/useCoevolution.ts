import { useCallback } from "react";
import { requestJson } from "../../../shared/api/http";
import { usePolling } from "../../../shared/api/usePolling";
import type { CoevolutionResponse } from "../types";

export function useCoevolution() {
  const load = useCallback(
    (signal: AbortSignal) => requestJson<CoevolutionResponse>("/api/arena/coevolution", { signal }),
    [],
  );
  return usePolling(load, 3000);
}
