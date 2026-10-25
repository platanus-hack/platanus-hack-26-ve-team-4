import { useCallback, useEffect } from "react";
import { useSearchParams } from "react-router";
import { errorMessage, isUnauthorized } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import { operatorRequest } from "../operator/api";
import { OperatorGate } from "../operator/OperatorGate";
import { ChatAudit } from "./ChatAudit";
import { ChatList } from "./ChatList";
import { moment } from "./labels";
import type { AuditRound, ChatDetail, ChatSummary } from "./types";
import "../monitor/monitor.css";
import "../participant/chat.css";
import "./audit.css";

const POLL_MS = 5000;

export function AuditPage() {
  return (
    <main className="audit-page">
      <OperatorGate
        intro={
          <>
            <p className="eyebrow">Yummi · Panel de la empresa</p>
            <h1>Auditoría de chats</h1>
          </>
        }
      >
        {(secret, logout) => <AuditBoard key={secret} secret={secret} logout={logout} />}
      </OperatorGate>
    </main>
  );
}

function AuditBoard({ secret, logout }: { secret: string; logout: (message?: string) => void }) {
  // La ronda y el chat viven en la URL: un enlace lleva directo a la conversación auditada.
  const [params, setParams] = useSearchParams();
  const archive = params.get("ronda");
  const selected = params.get("chat");
  const query = archive ? `?round=${encodeURIComponent(archive)}` : "";
  // Una ronda archivada no cambia: se lee una vez. La ronda en curso se refresca.
  const live = !archive;

  const loadRounds = useCallback(
    (signal: AbortSignal) =>
      operatorRequest<AuditRound[]>(secret, "/audit/rounds", undefined, signal),
    [secret],
  );
  const loadChats = useCallback(
    (signal: AbortSignal) =>
      operatorRequest<ChatSummary[]>(secret, `/audit/chats${query}`, undefined, signal),
    [secret, query],
  );
  const loadChat = useCallback(
    (signal: AbortSignal) =>
      operatorRequest<ChatDetail>(
        secret,
        `/audit/chats/${encodeURIComponent(selected ?? "")}${query}`,
        undefined,
        signal,
      ),
    [secret, selected, query],
  );
  const rounds = usePolling(loadRounds, 30000);
  const chats = usePolling(loadChats, live ? POLL_MS : 3_600_000);
  const chat = usePolling(loadChat, live ? POLL_MS : 3_600_000, Boolean(selected));
  const failure = rounds.error ?? chats.error;

  useEffect(() => {
    if (isUnauthorized(failure ?? chat.error)) logout("El secreto de operador fue rechazado.");
  }, [failure, chat.error, logout]);

  function choose(next: { ronda?: string | null; chat?: string | null }) {
    const merged = new URLSearchParams(params);
    for (const [key, value] of Object.entries(next)) {
      if (value) merged.set(key, value);
      else merged.delete(key);
    }
    setParams(merged);
  }

  const detail = chat.data && chat.data.id === selected ? chat.data : null;
  return (
    <div className="monitor audit">
      <header className="monitor-top">
        <div>
          <span className="monitor-label">Yummi · Panel de la empresa</span>
          <h1>Auditoría de chats</h1>
        </div>
        <div className="monitor-tags">
          <label className="monitor-label" htmlFor="audit-round">
            Ronda
          </label>
          <select
            id="audit-round"
            value={archive ?? ""}
            onChange={(event) => choose({ ronda: event.target.value || null, chat: null })}
          >
            {!rounds.data?.length && <option value="">En curso</option>}
            {rounds.data?.map((round) => (
              <option key={round.id ?? "actual"} value={round.id ?? ""}>
                {round.current
                  ? `En curso · ${round.round_id}`
                  : `${round.round_id} · archivada ${moment(round.started_at)}`}
              </option>
            ))}
          </select>
          <button type="button" className="monitor-chip" onClick={() => logout()}>
            Salir
          </button>
        </div>
      </header>
      {failure !== null && !isUnauthorized(failure) && (
        <p role="status" className="monitor-stale">
          {errorMessage(failure)} Los datos mostrados pueden estar desactualizados.
        </p>
      )}
      <div className="monitor-main">
        <ChatList
          chats={chats.data ?? []}
          selected={selected}
          onSelect={(id) => choose({ chat: id })}
        />
        {detail ? (
          <ChatAudit chat={detail} />
        ) : (
          <section className="monitor-panel" aria-label="Historial del chat">
            {chat.error !== null && selected && !isUnauthorized(chat.error) ? (
              <p role="alert">{errorMessage(chat.error)}</p>
            ) : (
              <p className="muted">
                {!chats.data
                  ? "Cargando chats…"
                  : selected
                    ? "Cargando historial…"
                    : chats.data.length
                      ? "Elige un chat para revisar todo su historial."
                      : "Esta ronda todavía no tiene chats."}
              </p>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
