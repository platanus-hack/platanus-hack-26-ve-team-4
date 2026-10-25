import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { errorMessage, isUnauthorized } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import { useArenaState } from "../arena/hooks/useArenaState";
import { ModeNotice } from "../arena/ModeNotice";
import { GuardPanel } from "../guard/GuardPanel";
import { AttemptList } from "./AttemptList";
import {
  type Campaign,
  type Evaluation,
  type Evidence,
  type Finding,
  type OperatorAttempt,
  operatorRequest,
  type Policy,
} from "./api";
import { DecoyPanel } from "./DecoyPanel";
import { EvaluationPanel } from "./EvaluationPanel";
import { downloadEvidence, EvidencePanel } from "./EvidencePanel";
import { OperatorGate } from "./OperatorGate";
import { PolicyList } from "./PolicyList";
import { TestChatPanel } from "./TestChatPanel";

export function OperatorPage() {
  return (
    <main className="page operator-page">
      <p className="eyebrow">Agent Zero · Acceso reservado</p>
      <h1>Operación</h1>
      <OperatorGate>
        {(secret, logout) => <OperatorDashboard key={secret} secret={secret} logout={logout} />}
      </OperatorGate>
    </main>
  );
}

function OperatorDashboard({
  secret,
  logout,
}: {
  secret: string;
  logout: (message?: string) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [evaluationReport, setEvaluationReport] = useState<unknown>(null);
  const [reason, setReason] = useState("");
  const [maxAttempts, setMaxAttempts] = useState(9);
  const [generation, setGeneration] = useState("templates");
  const actionLock = useRef(false);
  const mounted = useRef(true);
  const arena = useArenaState();
  const load = useCallback(
    async (signal: AbortSignal) => {
      const [policies, findings, attempts, campaigns, evaluations] = await Promise.all([
        operatorRequest<Policy[]>(secret, "/policies", undefined, signal),
        operatorRequest<Finding[]>(secret, "/findings", undefined, signal),
        operatorRequest<OperatorAttempt[]>(secret, "/attempts", undefined, signal),
        operatorRequest<Campaign[]>(secret, "/campaigns", undefined, signal),
        operatorRequest<Evaluation[]>(secret, "/evaluations", undefined, signal),
      ]);
      return { policies, findings, attempts, campaigns, evaluations };
    },
    [secret],
  );
  const operation = usePolling(load);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (isUnauthorized(operation.error))
      logout("La autorización no es válida o venció. Introduce el secreto de operador.");
  }, [operation.error, logout]);

  async function execute<T>(label: string, request: () => Promise<T>, done?: (result: T) => void) {
    if (actionLock.current) return;
    actionLock.current = true;
    setBusy(label);
    setError(null);
    setNotice(null);
    try {
      const result = await request();
      if (!mounted.current) return;
      done?.(result);
      operation.refresh();
      arena.refresh();
    } catch (cause) {
      if (!mounted.current) return;
      if (isUnauthorized(cause))
        logout("La autorización no es válida. Introduce el secreto de operador.");
      else setError(errorMessage(cause));
    } finally {
      actionLock.current = false;
      if (mounted.current) setBusy(null);
    }
  }
  function act(path: string, body: unknown = {}, message = "Operación completada.") {
    void execute(
      path,
      () => operatorRequest(secret, path, body),
      () => setNotice(message),
    );
  }
  function inspect(id: string) {
    void execute(
      "evidence",
      () => operatorRequest<Evidence>(secret, `/attempts/${id}`),
      setEvidence,
    );
  }
  function inspectEvaluation(id: string) {
    void execute(
      "evaluation-report",
      () => operatorRequest(secret, `/evaluations/${id}`),
      setEvaluationReport,
    );
  }
  function reset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void execute(
      "reset",
      () => operatorRequest<{ archive_id: string }>(secret, "/reset", { reason: reason.trim() }),
      (result) => {
        setEvidence(null);
        setEvaluationReport(null);
        setReason("");
        setNotice(
          `Nueva ronda abierta. Evidencia anterior archivada: ${result.archive_id}. Las sesiones previas ya no tienen acceso.`,
        );
      },
    );
  }
  const data = operation.data;
  const disabled = busy !== null;
  const inFlight =
    data?.attempts.some((attempt) => ["queued", "running"].includes(attempt.status)) ?? false;
  const activeCampaign = data?.campaigns.some((campaign) => campaign.status === "running") ?? false;
  const activeEvaluation =
    data?.evaluations.some((evaluation) => evaluation.status === "running") ?? false;

  return (
    <>
      <div className="section-heading">
        <p role="status">
          {busy
            ? "Procesando operación…"
            : operation.loading
              ? "Actualizando registro…"
              : "Conectado como operador"}
        </p>
        <button type="button" className="secondary" onClick={() => logout()}>
          Cerrar acceso
        </button>
      </div>
      {arena.data && <ModeNotice arena={arena.data} />}
      {error && <p role="alert">{error}</p>}
      {operation.error && !isUnauthorized(operation.error) && (
        <p role="alert">
          {errorMessage(operation.error)}{" "}
          {data
            ? "Se conserva el último registro recibido."
            : "No se pudieron cargar los registros."}
        </p>
      )}
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {!data ? (
        <button
          type="button"
          className="secondary"
          onClick={operation.refresh}
          disabled={operation.loading}
        >
          Volver a consultar
        </button>
      ) : (
        <>
          <section className="result">
            <h2>Control de ronda</h2>
            <p>
              {arena.data?.accepting ? "Entradas abiertas" : "Entradas cerradas"} · Política{" "}
              {arena.data?.policy_version ?? "—"} · {data.attempts.length} intentos conservados
            </p>
            <div className="controls">
              <button
                type="button"
                disabled={disabled || arena.data?.accepting === false}
                onClick={() =>
                  act("/arena/pause", {}, "Entradas pausadas. Los intentos aceptados continúan.")
                }
              >
                Pausar entradas
              </button>
              <button
                type="button"
                disabled={
                  disabled || arena.data?.accepting === true || arena.data?.revealed === true
                }
                onClick={() => act("/arena/resume", {}, "Entradas abiertas.")}
              >
                Abrir entradas
              </button>
              <button
                type="button"
                disabled={disabled || inFlight || arena.data?.revealed === true}
                onClick={() =>
                  act(
                    "/arena/reveal",
                    {},
                    "Ronda revelada. La clasificación final usa las violaciones confirmadas.",
                  )
                }
              >
                Revelar clasificación
              </button>
            </div>
            {inFlight && (
              <p className="muted">
                Espera al drenaje de intentos antes de revelar, revertir o reiniciar.
              </p>
            )}
            <details>
              <summary>Archivar e iniciar otra ronda</summary>
              <p>
                Conserva la evidencia anterior en un archivo, restaura fixtures y política base, e
                invalida las sesiones de participantes. No cambia el presupuesto global del
                proveedor.
              </p>
              <form onSubmit={reset}>
                <label htmlFor="reset-reason">Motivo del nuevo ensayo</label>
                <input
                  id="reset-reason"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  maxLength={500}
                  minLength={1}
                  required
                />
                <button
                  type="submit"
                  disabled={
                    disabled || inFlight || activeCampaign || activeEvaluation || !reason.trim()
                  }
                >
                  Archivar e iniciar nueva ronda
                </button>
              </form>
            </details>
          </section>
          <TestChatPanel secret={secret} />
          {evidence && <EvidencePanel evidence={evidence} close={() => setEvidence(null)} />}
          <section className="result">
            <h2>Prober</h2>
            <p className="muted">
              Genera ataques de laboratorio con origen autónomo y presupuesto separado de la
              audiencia.
            </p>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                act(
                  "/campaigns",
                  { max_attempts: maxAttempts, generation, max_mutations: maxAttempts },
                  "Campaña del Prober encolada.",
                );
              }}
            >
              <label htmlFor="campaign-max">Máximo de intentos</label>
              <input
                id="campaign-max"
                type="number"
                min={1}
                max={30}
                value={maxAttempts}
                onChange={(event) => setMaxAttempts(Number(event.target.value))}
                required
              />
              <label htmlFor="campaign-generation">Generación de casos</label>
              <select
                id="campaign-generation"
                value={generation}
                onChange={(event) => setGeneration(event.target.value)}
              >
                <option value="templates">Plantillas reproducibles</option>
                <option value="llm">Mutación con modelo</option>
                <option value="adaptive">Adaptativa con presupuesto por versión</option>
              </select>
              <button
                type="submit"
                disabled={disabled || activeCampaign || arena.data?.accepting === false}
              >
                Lanzar Prober
              </button>
            </form>
            {data.campaigns.map((campaign) => (
              <article className="result nested" key={campaign.id}>
                <p>
                  <strong>{campaign.status}</strong> · {campaign.attempt_ids.length}/
                  {campaign.max_attempts} intentos · {campaign.generation ?? "templates"}
                  {campaign.generation_calls !== undefined
                    ? ` · ${campaign.generation_calls} llamadas de generación`
                    : ""}
                </p>
                {campaign.stop_reason && <p>{campaign.stop_reason}</p>}
                {campaign.cases && campaign.cases.length > 0 && (
                  <details>
                    <summary>Casos generados y superficies</summary>
                    {campaign.cases.map((item) => (
                      <article key={item.digest}>
                        <p>
                          Caso {item.index + 1} · {item.status} · {item.case.family} ·{" "}
                          {item.case.surface}
                        </p>
                        {item.case.messages?.map((message) => (
                          <p className="reply" key={message}>
                            {message}
                          </p>
                        ))}
                        {item.error && <p>{item.error}</p>}
                        {item.attempt_id && (
                          <button
                            type="button"
                            className="secondary"
                            disabled={disabled}
                            onClick={() => inspect(item.attempt_id ?? "")}
                          >
                            Evidencia de este caso
                          </button>
                        )}
                      </article>
                    ))}
                  </details>
                )}
                {campaign.status === "running" && (
                  <button
                    type="button"
                    className="secondary"
                    disabled={disabled}
                    onClick={() =>
                      act(
                        `/campaigns/${campaign.id}/stop`,
                        {},
                        "Generación detenida; los intentos aceptados conservan su evidencia.",
                      )
                    }
                  >
                    Detener campaña
                  </button>
                )}
              </article>
            ))}
          </section>
          <PolicyList
            policies={data.policies}
            disabled={disabled || inFlight}
            rollback={(version) =>
              act(
                `/policies/${version}/rollback`,
                { reason: "Reversión desde operación" },
                "Política revertida a su padre verificado.",
              )
            }
          />
          <section>
            <h2>Hallazgos · {data.findings.length}</h2>
            {!data.findings.length && <p>Sin violaciones confirmadas.</p>}
            {data.findings.map((finding) => (
              <article className="result" key={finding.id}>
                <h3>
                  {finding.objective_id} · {finding.status}
                </h3>
                <p>{finding.probable_cause}</p>
                {finding.analysis?.status === "available" && (
                  <details>
                    <summary>
                      Interpretación del analizador · {finding.analysis.attack_family}
                    </summary>
                    <p>{finding.analysis.probable_cause}</p>
                    <ol>
                      {finding.analysis.reproduction_steps?.map((step) => (
                        <li key={step}>{step}</li>
                      ))}
                    </ol>
                    <p className="muted">
                      {finding.analysis.limitations} La evidencia del oráculo determina el hallazgo.
                    </p>
                  </details>
                )}
                <p>{finding.attempt_ids.length} intentos con evidencia.</p>
                <div className="controls">
                  {finding.attempt_ids.slice(0, 3).map((id) => (
                    <button
                      type="button"
                      className="secondary"
                      key={id}
                      disabled={disabled}
                      onClick={() => inspect(id)}
                    >
                      Evidencia {id.slice(-8)}
                    </button>
                  ))}
                </div>
              </article>
            ))}
          </section>
          <GuardPanel secret={secret} logout={logout} />
          <DecoyPanel secret={secret} />
          <EvaluationPanel
            policies={data.policies}
            evaluations={data.evaluations}
            busy={disabled}
            start={(body) => act("/evaluations", body, "Evaluación comparativa encolada.")}
            stop={(id) =>
              act(
                `/evaluations/${id}/stop`,
                {},
                "Evaluación detenida; se conserva el informe parcial.",
              )
            }
            inspect={inspectEvaluation}
          />
          {evaluationReport !== null && (
            <section className="result">
              <h2>Informe de evaluación</h2>
              <button
                type="button"
                className="secondary"
                onClick={() => downloadEvidence(evaluationReport, "agent-zero-evaluation")}
              >
                Descargar informe JSON
              </button>
              <details>
                <summary>Ver informe completo y casos</summary>
                <pre className="evidence">{JSON.stringify(evaluationReport, null, 2)}</pre>
              </details>
            </section>
          )}
          <AttemptList
            attempts={data.attempts}
            disabled={disabled}
            inspect={inspect}
            replay={(id) =>
              act(
                `/attempts/${id}/replay`,
                {},
                "Repetición encolada en una sesión protegida limpia.",
              )
            }
          />
        </>
      )}
    </>
  );
}
