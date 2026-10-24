import { type FormEvent, useCallback, useEffect, useState } from "react";
import { AttemptList } from "./AttemptList";
import {
  type Campaign,
  type Finding,
  type OperatorAttempt,
  operatorRequest,
  type Policy,
} from "./api";
import { PolicyList } from "./PolicyList";

export function OperatorPage() {
  const [input, setInput] = useState("");
  const [secret, setSecret] = useState("");
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [attempts, setAttempts] = useState<OperatorAttempt[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<unknown>(null);

  const refresh = useCallback(async () => {
    const [nextPolicies, nextFindings, nextAttempts, nextCampaigns] = await Promise.all([
      operatorRequest<Policy[]>(secret, "/policies"),
      operatorRequest<Finding[]>(secret, "/findings"),
      operatorRequest<OperatorAttempt[]>(secret, "/attempts"),
      operatorRequest<Campaign[]>(secret, "/campaigns"),
    ]);
    setPolicies(nextPolicies);
    setFindings(nextFindings);
    setAttempts(nextAttempts);
    setCampaigns(nextCampaigns);
  }, [secret]);

  useEffect(() => {
    if (!secret) return;
    let active = true;
    async function load() {
      try {
        await refresh();
      } catch (cause) {
        if (active)
          setError(cause instanceof Error ? cause.message : "No pudimos cargar la operación.");
      }
    }
    void load();
    const timer = setInterval(load, 1500);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [secret, refresh]);

  function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSecret(input);
  }

  async function act(path: string, body: unknown = {}) {
    try {
      await operatorRequest(secret, path, body);
      setError(null);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "La operación falló.");
    }
  }

  async function inspect(id: string) {
    try {
      setEvidence(await operatorRequest(secret, `/attempts/${id}`));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No pudimos cargar la evidencia.");
    }
  }

  return (
    <main className="page">
      <h1>Operación</h1>
      <form onSubmit={login}>
        <label htmlFor="operator-secret">Secreto de operador</label>
        <input
          id="operator-secret"
          type="password"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          required
        />
        <button type="submit">Acceder</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {secret && policies.length > 0 && (
        <>
          <div className="controls">
            <button type="button" onClick={() => void act("/arena/pause")}>
              Pausar entradas
            </button>
            <button type="button" onClick={() => void act("/arena/resume")}>
              Abrir entradas
            </button>
            <button type="button" onClick={() => void act("/arena/reveal")}>
              Revelar clasificación
            </button>
            <button type="button" onClick={() => void act("/campaigns", { max_attempts: 9 })}>
              Lanzar Prober · 9 intentos
            </button>
          </div>
          {campaigns.map((campaign) => (
            <p key={campaign.id}>
              Prober: {campaign.status} · {campaign.attempt_ids.length} intentos.{" "}
              {campaign.status === "running" && (
                <button type="button" onClick={() => void act(`/campaigns/${campaign.id}/stop`)}>
                  Detener
                </button>
              )}
            </p>
          ))}
          <PolicyList
            policies={policies}
            rollback={(version) =>
              void act(`/policies/${version}/rollback`, { reason: "Reversión desde operación" })
            }
          />
          <h2>Hallazgos</h2>
          {findings.length === 0 && <p>Sin violaciones confirmadas.</p>}
          {findings.map((finding) => (
            <article className="result" key={finding.id}>
              <strong>
                {finding.objective_id} · {finding.status}
              </strong>
              <p>{finding.probable_cause}</p>
            </article>
          ))}
          <AttemptList
            attempts={attempts}
            inspect={inspect}
            replay={(id) => act(`/attempts/${id}/replay`)}
          />
          {evidence !== null && <pre className="evidence">{JSON.stringify(evidence, null, 2)}</pre>}
        </>
      )}
    </main>
  );
}
