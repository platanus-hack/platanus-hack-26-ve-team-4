import type { Policy } from "./api";

export function PolicyList({
  policies,
  rollback,
}: {
  policies: Policy[];
  rollback: (version: number) => void;
}) {
  return (
    <section>
      <h2>Políticas</h2>
      {policies.map((policy) => (
        <article className="result" key={policy.version}>
          <strong>
            Versión {policy.version} · {policy.status}
          </strong>
          <p>{policy.reason}</p>
          <p>{policy.rules.length ? policy.rules.join(", ") : "Base del laboratorio"}</p>
          {policy.validation.cases && (
            <p>
              Validación: {policy.validation.cases.filter((item) => item.passed).length}/
              {policy.validation.cases.length} casos.
            </p>
          )}
          {policy.status === "active" && policy.version > 0 && (
            <button type="button" onClick={() => rollback(policy.version)}>
              Revertir esta versión
            </button>
          )}
        </article>
      ))}
    </section>
  );
}
