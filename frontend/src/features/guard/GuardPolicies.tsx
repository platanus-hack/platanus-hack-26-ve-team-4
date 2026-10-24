import type { GuardPolicy } from "./api";
import { GuardPolicyCard } from "./GuardPolicyCard";

export function GuardPolicies({
  policies,
  disabled,
  activate,
  rollback,
}: {
  policies: GuardPolicy[];
  disabled: boolean;
  activate: (version: number) => void;
  rollback: (version: number) => void;
}) {
  return (
    <section aria-labelledby="guard-policies-title">
      <h3 id="guard-policies-title">Versiones de política · {policies.length}</h3>
      {!policies.length && <p>Este contrato aún no tiene versiones de política.</p>}
      {policies.map((policy) => (
        <GuardPolicyCard
          key={policy.version}
          policy={policy}
          disabled={disabled}
          activate={activate}
          rollback={rollback}
        />
      ))}
    </section>
  );
}
