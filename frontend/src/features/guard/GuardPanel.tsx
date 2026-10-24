import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage, isUnauthorized } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import {
  type ContractSummary,
  contractPath,
  type GuardFinding,
  type GuardPolicy,
  guardRequest,
} from "./api";
import { ContractRegister } from "./ContractRegister";
import { GuardFindings } from "./GuardFindings";
import { GuardPolicies } from "./GuardPolicies";
import "./guard.css";

const POLL_MS = 4000;

export function GuardPanel({
  secret,
  logout,
}: {
  secret: string;
  logout: (message?: string) => void;
}) {
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const lock = useRef(false);
  const handleUnauthorized = useCallback(
    (cause: unknown) => {
      if (!isUnauthorized(cause)) return false;
      logout("La autorización no es válida o venció. Introduce el secreto de operador.");
      return true;
    },
    [logout],
  );
  const loadContracts = useCallback(
    (signal: AbortSignal) => guardRequest<ContractSummary[]>(secret, "/contracts", { signal }),
    [secret],
  );
  const contracts = usePolling(loadContracts, POLL_MS);
  const list = contracts.data ?? [];
  const current = list.find((item) => item.contract_id === selected) ?? list[0];
  const currentId = current?.contract_id;
  const loadDetail = useCallback(
    async (signal: AbortSignal) => {
      if (!currentId) return null;
      const base = contractPath(currentId);
      const [policies, findings] = await Promise.all([
        guardRequest<GuardPolicy[]>(secret, `${base}/policies`, { signal }),
        guardRequest<GuardFinding[]>(secret, `${base}/findings`, { signal }),
      ]);
      return { policies, findings };
    },
    [secret, currentId],
  );
  const detail = usePolling(loadDetail, POLL_MS, currentId !== undefined);
  useEffect(() => {
    if (contracts.error) handleUnauthorized(contracts.error);
    if (detail.error) handleUnauthorized(detail.error);
  }, [contracts.error, detail.error, handleUnauthorized]);

  async function change(version: number, verb: "activate" | "rollback", done: string) {
    if (lock.current || !currentId) return;
    lock.current = true;
    setBusy(true);
    setActionError(null);
    setNotice(null);
    try {
      await guardRequest(secret, `${contractPath(currentId)}/policies/${version}/${verb}`, {
        method: "POST",
      });
      setNotice(done);
      detail.refresh();
    } catch (cause) {
      if (!handleUnauthorized(cause)) setActionError(errorMessage(cause));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const loadError = [contracts.error, detail.error].find(
    (cause) => cause && !isUnauthorized(cause),
  );

  return (
    <section className="guard-panel" aria-labelledby="guard-title">
      <h2 id="guard-title">Guard · contratos y políticas</h2>
      <p className="muted">
        Protege agentes de cualquier empresa a partir de un contrato YAML. Elige un contrato para
        revisar sus políticas y hallazgos.
      </p>
      {loadError !== undefined && <p role="alert">{errorMessage(loadError)}</p>}
      {actionError && <p role="alert">{actionError}</p>}
      <p role="status" aria-live="polite" className={notice ? "notice" : "muted"}>
        {notice ?? (contracts.loading && !contracts.data ? "Cargando contratos…" : "")}
      </p>
      {contracts.data && !list.length && <p>No hay contratos cargados.</p>}
      {list.length > 0 && (
        <>
          <label htmlFor="guard-contract">Contrato</label>
          <select
            id="guard-contract"
            value={currentId}
            onChange={(event) => setSelected(event.target.value)}
          >
            {list.map((item) => (
              <option key={item.contract_id} value={item.contract_id}>
                {item.name} ({item.contract_id}){item.source === "api" ? " · registrado" : ""}
              </option>
            ))}
          </select>
          {current && (
            <p className="muted">
              Versión {current.version} · {current.tools.length} herramientas ·{" "}
              {current.invariants.length} invariantes ({current.invariants.join(", ")}) ·{" "}
              {current.legitimate} tareas legítimas ·{" "}
              {current.auto_activate ? "activación automática" : "activación manual"}
            </p>
          )}
          {!detail.data && detail.loading && <p role="status">Cargando políticas…</p>}
          {detail.data && (
            <>
              <GuardPolicies
                policies={detail.data.policies}
                disabled={busy}
                activate={(v) => void change(v, "activate", `Versión ${v} activada.`)}
                rollback={(v) =>
                  void change(v, "rollback", `Versión ${v} revertida a su padre verificado.`)
                }
              />
              <GuardFindings findings={detail.data.findings} />
            </>
          )}
        </>
      )}
      <ContractRegister
        secret={secret}
        unauthorized={handleUnauthorized}
        registered={(contract) => {
          setSelected(contract.contract_id);
          contracts.refresh();
        }}
      />
    </section>
  );
}
