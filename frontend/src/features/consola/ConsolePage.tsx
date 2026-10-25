import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage, isUnauthorized } from "../../shared/api/http";
import { OperatorGate } from "../operator/OperatorGate";
import { createTestSession } from "../operator/testSession";
import { AttemptChat } from "../participant/AttemptChat";
import type { ArenaSession } from "../participant/types";
import "../participant/chat.css";
import {
  archiveSession,
  consoleAlias,
  loadConsoleSession,
  loadPastSessions,
  saveConsoleSession,
} from "./consoleSession";
import { LiveAudit } from "./LiveAudit";
import "./consola.css";

const REJECTED = "El secreto de operador fue rechazado.";

export function ConsolePage() {
  return (
    <main className="consola-page">
      <OperatorGate
        intro={
          <>
            <p className="eyebrow">Yummy · Panel de la empresa</p>
            <h1>Consola de pruebas</h1>
          </>
        }
      >
        {(secret, logout) => <ConsoleBoard key={secret} secret={secret} logout={logout} />}
      </OperatorGate>
    </main>
  );
}

function ConsoleBoard({ secret, logout }: { secret: string; logout: (message?: string) => void }) {
  const [session, setSession] = useState<ArenaSession | null>(loadConsoleSession);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Evita que el arranque, «Nueva sesión» o un vencimiento abran dos sesiones a la vez.
  const busy = useRef(false);

  const create = useCallback(
    async (previous: ArenaSession | null) => {
      if (busy.current) return;
      busy.current = true;
      setCreating(true);
      setError(null);
      try {
        const suffix = Math.random().toString(36).slice(2, 7);
        const created = await createTestSession(secret, consoleAlias(suffix));
        // La sesión anterior queda en «Sesiones anteriores» antes de reemplazarla.
        if (previous) archiveSession(previous);
        saveConsoleSession(created);
        setSession(created);
      } catch (cause) {
        setError(`No se pudo abrir la sesión de prueba. ${errorMessage(cause)}`);
        if (isUnauthorized(cause)) logout(REJECTED);
      } finally {
        busy.current = false;
        setCreating(false);
      }
    },
    [secret, logout],
  );

  useEffect(() => {
    if (!session) void create(null);
  }, [session, create]);

  const past = loadPastSessions();

  return (
    <>
      <header className="consola-head">
        <h1>Consola de pruebas</h1>
        <div className="consola-actions">
          <button type="button" onClick={() => void create(session)} disabled={creating}>
            {creating ? "Creando…" : "Nueva sesión"}
          </button>
          <select
            aria-label="Sesiones anteriores"
            value=""
            onChange={(event) => {
              if (event.target.value) {
                window.open(
                  `/auditoria?chat=${encodeURIComponent(event.target.value)}`,
                  "_blank",
                  "noopener",
                );
              }
            }}
          >
            <option value="">— Sesiones anteriores —</option>
            {past.map((item) => (
              <option key={item.id} value={item.id}>
                {item.alias}
              </option>
            ))}
          </select>
          {session && (
            <a href={`/auditoria?chat=${encodeURIComponent(session.id)}`}>Abrir en Auditoría</a>
          )}
          <button type="button" onClick={() => logout()}>
            Salir
          </button>
        </div>
      </header>
      {error && <p role="alert">{error}</p>}
      {session ? (
        <div className="consola-grid">
          <AttemptChat
            key={session.id}
            session={session}
            onExpired={() => {
              saveConsoleSession(null);
              setSession(null);
              void create(null);
            }}
          />
          <LiveAudit
            key={session.id}
            secret={secret}
            sessionId={session.id}
            onUnauthorized={() => logout(REJECTED)}
          />
        </div>
      ) : (
        creating && <p role="status">Abriendo sesión de prueba…</p>
      )}
    </>
  );
}
