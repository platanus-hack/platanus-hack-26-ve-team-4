import { type FormEvent, useCallback, useEffect, useState } from "react";
import { errorMessage, isUnauthorized } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import { useArenaState } from "../arena/hooks/useArenaState";
import { operatorRequest, type Policy } from "../operator/api";
import { AttemptDetailPanel } from "./AttemptDetailPanel";
import { AttemptFeed, type Filter } from "./AttemptFeed";
import { MonitorKpis } from "./MonitorKpis";
import { MonitorTrends } from "./MonitorTrends";
import { PolicyStory } from "./PolicyStory";
import type { Monitor } from "./types";
import "./monitor.css";

const POLL_MS = 4000;

export function MonitorPage() {
  const [input, setInput] = useState("");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);
  const logout = useCallback((message?: string) => {
    setSecret("");
    setError(message ?? null);
  }, []);
  function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!input.trim()) return;
    setError(null);
    setSecret(input);
    setInput("");
  }
  if (secret) return <MonitorDashboard key={secret} secret={secret} logout={logout} />;
  return (
    <main className="page monitor-page">
      <p className="eyebrow">Yummy · Panel de la empresa</p>
      <h1>Agent Zero Monitor</h1>
      <p>
        Interacciones con el agente de soporte, su resultado, el parche que las cerró y el consumo
        del modelo. El secreto permanece solo en memoria durante esta visita.
      </p>
      <form onSubmit={login}>
        <label htmlFor="monitor-secret">Secreto de operador</label>
        <input
          id="monitor-secret"
          type="password"
          autoComplete="off"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          required
        />
        <button type="submit">Acceder</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </main>
  );
}

function MonitorDashboard({
  secret,
  logout,
}: {
  secret: string;
  logout: (message?: string) => void;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<string | null>(null);
  const loadMonitor = useCallback(
    (signal: AbortSignal) => operatorRequest<Monitor>(secret, "/monitor", undefined, signal),
    [secret],
  );
  const loadPolicies = useCallback(
    (signal: AbortSignal) => operatorRequest<Policy[]>(secret, "/policies", undefined, signal),
    [secret],
  );
  const monitor = usePolling(loadMonitor, POLL_MS);
  const policies = usePolling(loadPolicies, POLL_MS);
  const arena = useArenaState();
  const failure = monitor.error ?? policies.error;

  useEffect(() => {
    if (isUnauthorized(failure)) logout("El secreto de operador fue rechazado.");
  }, [failure, logout]);

  const attempts = monitor.data?.attempts ?? [];
  const current = attempts.find((attempt) => attempt.id === selected) ?? attempts.at(-1) ?? null;
  const active = policies.data?.find((policy) => policy.status === "active");

  return (
    <main className="monitor">
      <header className="monitor-top">
        <div>
          <span className="monitor-label">
            Arena Yummy{arena.data?.round_id ? ` · ronda ${arena.data.round_id}` : ""}
          </span>
          <h1>Agent Zero Monitor</h1>
        </div>
        <div className="monitor-tags">
          <span className={`monitor-tag ${monitor.data?.llm_mode === "live" ? "is-live" : ""}`}>
            modo <b>{monitor.data?.llm_mode ?? "…"}</b>
          </span>
          <span className="monitor-tag">
            política activa <b>{active ? `v${active.version}` : "…"}</b>
          </span>
          <span className="monitor-tag">
            admisión <b>{arena.data?.accepting === false ? "pausada" : "abierta"}</b>
          </span>
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
      {monitor.data && <MonitorKpis monitor={monitor.data} />}
      <div className="monitor-main">
        <AttemptFeed
          attempts={attempts}
          filter={filter}
          onFilter={setFilter}
          selected={current?.id ?? null}
          onSelect={setSelected}
        />
        {current ? (
          <AttemptDetailPanel key={current.id} secret={secret} attempt={current} />
        ) : (
          <section className="monitor-panel" aria-label="Detalle de la interacción">
            <p className="muted">
              {monitor.data
                ? "Todavía no hay interacciones en esta ronda."
                : "Cargando interacciones…"}
            </p>
          </section>
        )}
      </div>
      {policies.data && <PolicyStory policies={policies.data} attempts={attempts} />}
      {monitor.data && <MonitorTrends attempts={attempts} />}
    </main>
  );
}
