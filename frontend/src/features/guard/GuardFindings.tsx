import type { GuardFinding } from "./api";

export function GuardFindings({ findings }: { findings: GuardFinding[] }) {
  return (
    <section aria-labelledby="guard-findings-title">
      <h3 id="guard-findings-title">Hallazgos del Guard · {findings.length}</h3>
      {!findings.length && <p>Sin invariantes rotos.</p>}
      {findings.map((finding) => (
        <article className="result" key={finding.id}>
          <p>
            <strong>Invariantes rotos:</strong> {finding.invariant_ids.join(", ")}
          </p>
          <p className="muted">
            Detectado con la versión {finding.policy_version} ·{" "}
            {finding.resolved_by === null
              ? "sin resolver"
              : `resuelto por la versión ${finding.resolved_by}`}
          </p>
        </article>
      ))}
    </section>
  );
}
