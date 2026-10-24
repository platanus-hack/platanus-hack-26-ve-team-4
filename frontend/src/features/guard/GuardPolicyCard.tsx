import type { GuardPolicy, PolicyStatus } from "./api";
import { GuardGate } from "./GuardGate";

const STATUS_LABELS: Record<PolicyStatus, string> = {
  active: "activa",
  proposed: "propuesta",
  superseded: "reemplazada",
  rolled_back: "revertida",
  rejected: "rechazada",
};

export function GuardPolicyCard({
  policy,
  disabled,
  activate,
  rollback,
}: {
  policy: GuardPolicy;
  disabled: boolean;
  activate: (version: number) => void;
  rollback: (version: number) => void;
}) {
  const date = new Date(policy.created_at);
  return (
    <article className="result guard-policy">
      <h4>
        Versión {policy.version} ·{" "}
        <span className={`guard-status ${policy.status}`}>
          {STATUS_LABELS[policy.status] ?? policy.status}
        </span>
      </h4>
      <p className="muted">
        Padre: {policy.parent_version === null ? "ninguno" : `versión ${policy.parent_version}`} ·{" "}
        <time dateTime={policy.created_at}>
          {Number.isNaN(date.getTime()) ? policy.created_at : date.toLocaleString("es")}
        </time>
      </p>
      {policy.rules.length ? (
        <ul className="guard-rules">
          {policy.rules.map((rule) => (
            <li key={rule.rule_id}>
              <code>{rule.text}</code>
            </li>
          ))}
        </ul>
      ) : (
        <p>Sin reglas.</p>
      )}
      <GuardGate gate={policy.report.gate} />
      {policy.status === "proposed" && (
        <button type="button" disabled={disabled} onClick={() => activate(policy.version)}>
          Activar versión {policy.version}
        </button>
      )}
      {policy.status === "active" && (
        <button
          type="button"
          className="secondary"
          disabled={disabled}
          onClick={() => rollback(policy.version)}
        >
          Revertir versión {policy.version}
        </button>
      )}
    </article>
  );
}
