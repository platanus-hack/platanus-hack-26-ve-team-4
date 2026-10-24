import { useEffect, useState } from "react";
import { requestJson } from "../../../shared/api/http";
import type { TraceEvent } from "../types";
import type { Replay } from "./types";

const FLASH_AT_MS = 2000;
const SEAL_AT_MS = 3200;

export function validatedVersion(events: TraceEvent[]): number | null {
  const found = events.find(
    (event) =>
      event.type === "patch_validated" &&
      event.data.passed === true &&
      Number.isSafeInteger(event.data.version),
  );
  return found ? (found.data.version as number) : null;
}

export function prefersReducedMotion() {
  return typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;
}

export function useReplay(events: TraceEvent[]) {
  const version = validatedVersion(events);
  const [replay, setReplay] = useState<Replay | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (version === null) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    requestJson<Replay>(`/api/arena/replay/${version}`, { signal: controller.signal })
      .then((body) => setReplay(body))
      .catch((failure) => {
        if (controller.signal.aborted) return;
        setReplay(null);
        setError(failure);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [version]);

  return { replay, loading, error };
}

export function useReplayPhase(version: number | undefined) {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    if (version === undefined) return;
    if (prefersReducedMotion()) {
      setPhase(2);
      return;
    }
    setPhase(0);
    const flash = setTimeout(() => setPhase(1), FLASH_AT_MS);
    const seal = setTimeout(() => setPhase(2), SEAL_AT_MS);
    return () => {
      clearTimeout(flash);
      clearTimeout(seal);
    };
  }, [version]);
  return phase;
}
