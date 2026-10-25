import type { Evidence } from "./api";

export function downloadEvidence(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${name}.json`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const ACCESS_WITHOUT_DISCLOSURE_LABEL = "Accedió al dato sin mostrarlo";

export function EvidencePanel({ evidence, close }: { evidence: Evidence; close: () => void }) {
  return (
    <section className="evidence-panel" aria-label="Evidencia del intento">
      <div className="section-heading">
        <h2>Evidencia · política {evidence.policy_version}</h2>
        <button type="button" className="secondary" onClick={close}>
          Cerrar evidencia
        </button>
      </div>
      <p>
        <code>{evidence.id}</code> · {evidence.route} · {evidence.outcome ?? evidence.status}
      </p>
      {evidence.messages?.map((message, index) => (
        <p className="reply" key={["first", "second", "third", "fourth"][index]}>
          <strong>Turno {index + 1}:</strong> {message}
        </p>
      ))}
      {evidence.reply && (
        <p className="reply">
          <strong>Respuesta:</strong> {evidence.reply}
        </p>
      )}
      {evidence.assessment?.verdicts?.map((verdict) => (
        <article className="result" key={verdict.objective_id}>
          <strong>
            {verdict.objective_id}: {verdict.violated ? "Violado" : "Sin violación observada"}
          </strong>
          {evidence.outcome === "confirmed_violation" &&
            verdict.violated &&
            verdict.level === "action" && (
              <p>
                <span className="badge danger">{ACCESS_WITHOUT_DISCLOSURE_LABEL}</span>
              </p>
            )}
          <p>{verdict.detail}</p>
          <p className="muted">
            Nivel: {verdict.level ?? "—"} · Eventos:{" "}
            {verdict.evidence_event_ids?.join(", ") || "Sin efecto indebido observado"}
          </p>
        </article>
      ))}
      <h3>Traza de herramientas y controles</h3>
      <ol className="timeline">
        {evidence.events?.map((event) => (
          <li className="trace-event" key={event.id}>
            <strong>{event.type}</strong>
            <time dateTime={event.timestamp}>
              {new Date(event.timestamp).toLocaleTimeString("es")}
            </time>
            <pre className="evidence">{JSON.stringify(event.data, null, 2)}</pre>
          </li>
        ))}
      </ol>
      <div className="controls">
        <button
          className="secondary"
          type="button"
          onClick={() => downloadEvidence(evidence, evidence.id)}
        >
          Descargar evidencia JSON
        </button>
      </div>
      <details>
        <summary>Registro completo</summary>
        <pre className="evidence">{JSON.stringify(evidence, null, 2)}</pre>
      </details>
    </section>
  );
}
