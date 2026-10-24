import { useCallback, useEffect, useState } from "react";

/** Serial polling. A slow response never overlaps the next request, and stale responses
 * cannot replace a newer credential/round after their owner has been disposed. */
export function usePolling<T>(
  load: (signal: AbortSignal) => Promise<T>,
  intervalMs = 2000,
  enabled = true,
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const refresh = useCallback(() => setRevision((value) => value + 1), []);
  // Revision is intentionally part of the request lifetime.
  useEffect(() => {
    void revision;
    if (!enabled) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      setLoading(true);
      try {
        const result = await load(controller.signal);
        if (!controller.signal.aborted) {
          setData(result);
          setError(null);
        }
      } catch (cause) {
        if (!controller.signal.aborted) setError(cause);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          timer = setTimeout(poll, intervalMs);
        }
      }
    }
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [load, intervalMs, enabled, revision]);
  return { data, error, loading, refresh };
}
