import type { Policy } from "./api";
import "./flowPolicy.css";

const ORIGINS: Record<string, string> = {
  user: "mensaje del cliente",
  store: "datos de la tienda",
  untrusted: "documento o resultado no confiable",
  memory: "memoria no confiable",
  model: "sin origen observado",
};
const LOW_INTEGRITY = new Set(["untrusted", "memory"]);

function ProvenanceChain({ policy }: { policy: Policy }) {
  const rows = new Map<string, { tool: string; argument: string; origin: string }>();
  for (const call of policy.synthesis?.trace ?? []) {
    for (const [argument, origin] of Object.entries(call.provenance)) {
      rows.set(`${call.tool}:${argument}:${origin}`, { tool: call.tool, argument, origin });
    }
  }
  if (!rows.size) return null;
  return (
    <ul className="flow-trace" aria-label="Procedencia de la traza original">
      {[...rows].map(([key, row]) => (
        <li key={key} className={LOW_INTEGRITY.has(row.origin) ? "flow-low" : undefined}>
          {ORIGINS[row.origin] ?? row.origin} → <code>{row.argument}</code> de{" "}
          <code>{row.tool}</code>
          {LOW_INTEGRITY.has(row.origin) ? " · integridad baja" : ""}
        </li>
      ))}
    </ul>
  );
}

function IntegrityProbe({ policy }: { policy: Policy }) {
  const effects = policy.validation.integrity_probe?.untrusted_effects;
  if (effects === undefined) return null;
  return (
    <p className={effects ? "flow-warning" : "flow-ok"}>
      Sonda de integridad (reembolso de 10 USD inyectado por un resultado de herramienta):{" "}
      {effects
        ? `${effects} efecto(s) ejecutado(s) con argumentos no confiables`
        : "ningún efecto con argumentos no confiables"}
    </p>
  );
}

export function FlowPolicyPanel({ policy }: { policy: Policy }) {
  const rules = policy.flow_rules ?? [];
  const rejected = policy.validation.synthesis;
  const gate = policy.synthesis?.precheck;
  return (
    <>
      {rules.length > 0 && (
        <div className="flow-policy">
          <h4>
            {policy.synthesis?.source === "synthesized"
              ? "Política de flujo sintetizada desde el hallazgo"
              : "Reglas de flujo heredadas"}
          </h4>
          <ProvenanceChain policy={policy} />
          <ol className="flow-rules">
            {rules.map((rule) => (
              <li key={rule.rule_id}>
                <code>{rule.text}</code> <span className="muted">{rule.reason}</span>
              </li>
            ))}
          </ol>
          {gate && (
            <p className="flow-ok">
              Compuerta determinista: bloquea {gate.original_blocked}/{gate.original_total} llamadas
              de la traza · conserva {gate.legitimate_kept}/{gate.legitimate_total} llamadas
              legítimas
            </p>
          )}
          {policy.synthesis?.llm_mode === "demo" && (
            <p className="muted">Modo demo: reglas derivadas de la traza, no de un proveedor.</p>
          )}
        </div>
      )}
      {rejected?.status && rejected.status !== "accepted" && (
        <p className="flow-warning">
          Síntesis {rejected.status === "rejected" ? "rechazada" : "no disponible"}
          {rejected.precheck ? `: ${rejected.precheck.reason}` : ""} Se usó el catálogo.
        </p>
      )}
      <IntegrityProbe policy={policy} />
    </>
  );
}
