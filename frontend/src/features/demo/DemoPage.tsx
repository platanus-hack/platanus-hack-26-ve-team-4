import { useCallback, useEffect, useMemo, useState } from "react";
import { isUnauthorized } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import { loadBoard } from "../board/api";
import type { LiveAttempt } from "../board/types";
import { OperatorGate } from "../operator/OperatorGate";
import { caseById, kindOf } from "./catalog";
import { DemoChat } from "./DemoChat";
import { DemoSummary } from "./DemoSummary";
import { LaunchDialog } from "./LaunchDialog";
import { useSwarm } from "./useSwarm";
import { summarize, verdictOf } from "./verdict";
import "./demo.css";

const REJECTED = "El secreto de operador fue rechazado.";

export function DemoPage() {
  return (
    <main className="demo-page">
      <OperatorGate
        intro={
          <>
            <p className="eyebrow">Escala de intención humana 0–5</p>
            <h1>Chats automáticos en vivo</h1>
          </>
        }
      >
        {(secret, logout) => <DemoBoard key={secret} secret={secret} logout={logout} />}
      </OperatorGate>
    </main>
  );
}

function useElapsed(startedAt: number | null, finishedAt: number | null): number {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    if (startedAt === null || finishedAt !== null) return;
    const timer = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(timer);
  }, [startedAt, finishedAt]);
  if (startedAt === null) return 0;
  return ((finishedAt ?? now) - startedAt) / 1000;
}

function DemoBoard({ secret, logout }: { secret: string; logout: (message?: string) => void }) {
  const swarm = useSwarm(secret);
  const [dialog, setDialog] = useState(false);
  const load = useCallback((signal: AbortSignal) => loadBoard(secret, signal), [secret]);
  const board = usePolling(load, 1500, swarm.runs.length > 0);
  const seconds = useElapsed(swarm.startedAt, swarm.finishedAt);

  useEffect(() => {
    if (isUnauthorized(board.error)) logout(REJECTED);
  }, [board.error, logout]);

  const live = useMemo(() => {
    const byId = new Map<string, LiveAttempt>();
    for (const session of board.data?.sessions ?? [])
      for (const attempt of session.attempts) byId.set(attempt.id, attempt);
    return byId;
  }, [board.data]);

  const chats = swarm.runs.map((run) => {
    const item = caseById(run.caseId);
    const attempts = run.turns
      .map((turn) => (turn.attempt ? live.get(turn.attempt.id) : undefined))
      .filter((attempt): attempt is LiveAttempt => Boolean(attempt));
    const verdict = verdictOf(kindOf(item), attempts, run.phase === "done");
    return { run, item, verdict, kind: kindOf(item) };
  });

  return (
    <>
      <header className="demo-head">
        <div>
          <p className="eyebrow">
            Escala de intención humana 0–5 · modo {board.data?.llm_mode ?? "…"}
          </p>
          <h1>Chats automáticos en vivo</h1>
        </div>
        <div className="demo-actions">
          {swarm.running ? (
            <button type="button" onClick={swarm.stop}>
              Detener
            </button>
          ) : (
            <button type="button" className="primary" onClick={() => setDialog(true)}>
              Lanzar chats automáticos
            </button>
          )}
          <button type="button" onClick={() => logout()}>
            Salir
          </button>
        </div>
      </header>
      {chats.length > 0 && <DemoSummary summary={summarize(chats)} seconds={seconds} />}
      {chats.length === 0 && (
        <p className="demo-empty">
          Elige cuántos chats y qué casos: todos arrancan a la vez contra este entorno y aquí se lee
          cada conversación, su ruta y su veredicto en vivo.
        </p>
      )}
      <section className={`demo-grid n-${chats.length}`}>
        {chats.map(({ run, item, verdict }) => (
          <DemoChat key={run.key} item={item} run={run} live={live} verdict={verdict} />
        ))}
      </section>
      {dialog && (
        <LaunchDialog
          onClose={() => setDialog(false)}
          onLaunch={(ids) => {
            setDialog(false);
            swarm.launch(ids);
          }}
        />
      )}
    </>
  );
}
