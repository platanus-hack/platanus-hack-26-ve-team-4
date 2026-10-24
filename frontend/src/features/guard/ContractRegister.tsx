import { type FormEvent, useState } from "react";
import { errorMessage } from "../../shared/api/http";
import { type ContractSummary, guardRequest, type ValidationResult } from "./api";

export function ContractRegister({
  secret,
  unauthorized,
  registered,
}: {
  secret: string;
  unauthorized: (cause: unknown) => boolean;
  registered: (contract: ContractSummary) => void;
}) {
  const [yaml, setYaml] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  async function run(action: () => Promise<{ ok: boolean; text: string }>) {
    setBusy(true);
    setMessage(null);
    try {
      setMessage(await action());
    } catch (cause) {
      if (!unauthorized(cause)) setMessage({ ok: false, text: errorMessage(cause) });
    } finally {
      setBusy(false);
    }
  }
  function validate() {
    void run(async () => {
      const result = await guardRequest<ValidationResult>(secret, "/contracts/validate", { yaml });
      if (!result.valid) return { ok: false, text: `Contrato inválido: ${result.error}` };
      const { contract } = result;
      return {
        ok: true,
        text: `Contrato válido: ${contract.name} (${contract.contract_id}) con ${contract.tools.length} herramientas y ${contract.invariants.length} invariantes.`,
      };
    });
  }
  function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(async () => {
      const result = await guardRequest<{ contract: ContractSummary }>(secret, "/contracts", {
        yaml,
      });
      registered(result.contract);
      setYaml("");
      return { ok: true, text: `Contrato ${result.contract.contract_id} registrado.` };
    });
  }
  return (
    <form className="guard-register" onSubmit={register} aria-busy={busy}>
      <h3>Registrar contrato</h3>
      <label htmlFor="guard-yaml">Contrato en YAML</label>
      <textarea
        id="guard-yaml"
        rows={10}
        spellCheck={false}
        value={yaml}
        onChange={(event) => setYaml(event.target.value)}
        required
      />
      <div className="controls">
        <button
          type="button"
          className="secondary"
          disabled={busy || !yaml.trim()}
          onClick={validate}
        >
          Validar
        </button>
        <button type="submit" disabled={busy || !yaml.trim()}>
          Registrar
        </button>
      </div>
      <p
        className="guard-message"
        role={message?.ok === false ? "alert" : "status"}
        aria-live="polite"
      >
        {busy ? "Procesando…" : message?.text}
      </p>
    </form>
  );
}
