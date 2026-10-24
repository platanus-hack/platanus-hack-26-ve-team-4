import type { Policy } from "./api";
import { FlowPolicyPanel } from "./FlowPolicyPanel";

const RULE_LABELS: Record<string, string> = {
  order_belongs_to_session_customer: "La identidad solo puede acceder a sus propios pedidos",
  refund_within_limit: "Reembolsos positivos con máximo acumulado de 20 USD por pedido",
  memory_key_allowlist: "La memoria solo conserva preferencias sin conceder permisos",
  require_provenance: "Las fuentes deben conservar su procedencia",
};
export function PolicyList({
  policies,
  rollback,
  disabled,
}: {
  policies: Policy[];
  rollback: (version: number) => void;
  disabled: boolean;
}) {
  return (
    <section>
      <h2>Políticas y validación</h2>
      {policies.map((policy) => (
        <article className="result" key={policy.version}>
          <h3>
            Versión {policy.version} · {policy.status}
          </h3>
          <p>{policy.reason}</p>
          {policy.validation.reason && <p>Resultado de validación: {policy.validation.reason}</p>}
          {policy.analysis?.status === "available" && policy.analysis.explanation && (
            <details>
              <summary>Explicación orientativa del Patcher</summary>
              <p>{policy.analysis.explanation.rationale}</p>
              <p>{policy.analysis.explanation.expected_effect}</p>
              <p>Riesgos de regresión a verificar:</p>
              <ul>
                {policy.analysis.explanation.regression_risks.map((risk) => (
                  <li key={risk}>{risk}</li>
                ))}
              </ul>
              <p className="muted">
                {policy.analysis.explanation.limitations} La activación depende de las pruebas.
              </p>
            </details>
          )}
          <FlowPolicyPanel policy={policy} />
          {policy.rules.length ? (
            <ul>
              {policy.rules.map((rule) => (
                <li key={rule}>{RULE_LABELS[rule] ?? rule}</li>
              ))}
            </ul>
          ) : policy.flow_rules?.length ? null : (
            <p>Base vulnerable del laboratorio.</p>
          )}
          {policy.validation.cases && (
            <details>
              <summary>
                Validación: {policy.validation.cases.filter((item) => item.passed).length}/
                {policy.validation.cases.length} casos ·{" "}
                {policy.validation.passed ? "Aprobada" : "Rechazada o pendiente"}
              </summary>
              <ul>
                {policy.validation.cases.map((item) => (
                  <li key={item.name}>
                    {item.passed ? "✓ Aprobado" : "✕ Falló"} · {item.name}
                    {item.error ? ` · ${item.error}` : ""}
                  </li>
                ))}
              </ul>
            </details>
          )}
          {policy.content_hash && (
            <p className="muted hash">
              Hash: <code>{policy.content_hash}</code>
            </p>
          )}
          {policy.status === "active" && policy.version > 0 && (
            <button
              className="secondary"
              type="button"
              disabled={disabled}
              onClick={() => rollback(policy.version)}
            >
              Revertir a la versión anterior
            </button>
          )}
        </article>
      ))}
    </section>
  );
}
