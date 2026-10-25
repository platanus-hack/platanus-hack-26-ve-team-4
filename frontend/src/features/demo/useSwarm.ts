import { useCallback, useEffect, useRef, useState } from "react";
import { caseById } from "./catalog";
import { type ChatRun, chatAlias, runChat, TIMING, type Timing } from "./runner";

export interface Swarm {
  runs: ChatRun[];
  running: boolean;
  startedAt: number | null;
  finishedAt: number | null;
  launch: (caseIds: string[]) => void;
  stop: () => void;
}

export function useSwarm(secret: string, timing: Timing = TIMING): Swarm {
  const [runs, setRuns] = useState<ChatRun[]>([]);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [finishedAt, setFinishedAt] = useState<number | null>(null);
  const controller = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    if (!controller.current) return;
    controller.current.abort();
    controller.current = null;
    setFinishedAt(Date.now());
  }, []);

  useEffect(() => stop, [stop]);

  const launch = useCallback(
    (caseIds: string[]) => {
      stop();
      const current = new AbortController();
      controller.current = current;
      const stamp = Date.now().toString(36).slice(-3);
      const initial = caseIds.map((id, index) => ({
        key: `${stamp}-${index}`,
        caseId: id,
        alias: chatAlias(caseById(id), Number.parseInt(stamp, 36) % 1000),
        sessionId: null,
        phase: "creating" as const,
        turns: [],
        error: null,
      }));
      setRuns(initial);
      setStartedAt(Date.now());
      setFinishedAt(null);
      const update = (next: ChatRun) =>
        setRuns((all) => all.map((run) => (run.key === next.key ? next : run)));
      void Promise.all(
        initial.map((run) =>
          runChat(secret, caseById(run.caseId), run, update, current.signal, timing),
        ),
      ).then(() => {
        if (!current.signal.aborted) setFinishedAt(Date.now());
        if (controller.current === current) controller.current = null;
      });
    },
    [secret, stop, timing],
  );

  const running = startedAt !== null && finishedAt === null && runs.length > 0;
  return { runs, running, startedAt, finishedAt, launch, stop };
}
