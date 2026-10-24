import { useCallback } from "react";
import { usePolling } from "../../shared/api/usePolling";
import { useArenaState } from "../arena/hooks/useArenaState";
import { ModeNotice } from "../arena/ModeNotice";
import { formatDuration } from "../participant/RevealCard";
import { type DecoyRate, type DecoySummary, operatorRequest } from "./api";

function rateText(rate: DecoyRate): string {
  const share = rate.value === null ? "" : ` · ${Math.round(rate.value * 100)} %`;
  return `${rate.k}/${rate.n}${share}`;
}

export function DecoyPanel({ secret }: { secret: string }) {
  const load = useCallback(
    (signal: AbortSignal) => operatorRequest<DecoySummary>(secret, "/decoy", undefined, signal),
    [secret],
  );
  const { data, error } = usePolling(load, 5000);
  const arena = useArenaState().data;

  return (
    <section className="result">
      <h2>Señuelo medido</h2>
      {arena && <ModeNotice arena={arena} />}
      {data === null && <p className="muted">{error ? "Sin datos del señuelo." : "Cargando…"}</p>}
      {data !== null && data.diverted_n === 0 && (
        <p>Todavía ninguna sesión de la audiencia pasó al señuelo (n = 0).</p>
      )}
      {data !== null && data.diverted_n > 0 && (
        <>
          <p>
            n = {data.diverted_n} sesiones desviadas de la audiencia
            {data.excluded_autonomous_n > 0 &&
              ` · ${data.excluded_autonomous_n} del Prober excluidas`}
            .
          </p>
          {data.small_n ? (
            <p className="muted">
              Con menos de 5 sesiones no se publican porcentajes: se muestran los casos.
            </p>
          ) : (
            <ul>
              <li>Retenidas: {rateText(data.retained)}</li>
              <li>Cebo tomado: {rateText(data.bait_taken)}</li>
              <li>Engañadas (credencial reutilizada): {rateText(data.deceived)}</li>
              {data.median_retained_seconds !== null && (
                <li>Retención mediana: {formatDuration(data.median_retained_seconds)}</li>
              )}
            </ul>
          )}
          <div className="decoy-table-wrap">
            <table className="decoy-table">
              <thead>
                <tr>
                  <th>Alias</th>
                  <th>Motivo</th>
                  <th>Retención</th>
                  <th>Pasos</th>
                  <th>Intentos</th>
                  <th>Cebos</th>
                  <th>Credencial reutilizada</th>
                </tr>
              </thead>
              <tbody>
                {data.cases.map((item) => (
                  <tr key={item.session_id}>
                    <td>{item.alias}</td>
                    <td>{item.reason}</td>
                    <td>{formatDuration(item.retained_seconds)}</td>
                    <td>{item.post_diversion_steps}</td>
                    <td>{item.post_diversion_attempts}</td>
                    <td>{item.honeytools_touched.join(", ") || "—"}</td>
                    <td>{item.token_reused ? "sí" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <p className="muted">
        Definiciones y salvedades en docs/dominio/decoy.md. Sin atacantes externos, estas cifras
        describen a la audiencia de esta ronda, no una tasa general de engaño.
      </p>
    </section>
  );
}
