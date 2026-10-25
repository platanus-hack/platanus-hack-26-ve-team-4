import { outcomeOf, tokensText, totalTokens } from "./labels";
import type { MonitorAttempt } from "./types";

function ViolationRate({ attempts }: { attempts: MonitorAttempt[] }) {
  const versions = [...new Set(attempts.map((attempt) => attempt.policy_version))].sort(
    (a, b) => a - b,
  );
  const rows = versions.map((version) => {
    // Solo la ruta protegida con veredicto: el señuelo y los inconclusos no son defensa.
    const scoped = attempts.filter(
      (attempt) =>
        attempt.policy_version === version &&
        attempt.route === "protected" &&
        attempt.outcome !== null &&
        attempt.outcome !== "inconclusive",
    );
    const violated = scoped.filter((attempt) => attempt.outcome === "confirmed_violation").length;
    return { version, n: scoped.length, k: violated };
  });
  return (
    <section className="monitor-panel">
      <h2>Tasa de violación por versión</h2>
      <p className="muted monitor-small">
        Ruta protegida, sin señuelo ni inconclusos. Con n pequeño describe la ronda, no estima
        eficacia.
      </p>
      <div className="monitor-bars">
        {rows.map((row) => (
          <div key={row.version} className="monitor-bar">
            <b>v{row.version}</b>
            <span className="monitor-track">
              <i style={{ width: `${row.n ? (row.k / row.n) * 100 : 0}%` }} />
            </span>
            <span className="monitor-n">
              {row.k}/{row.n}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function TokenBars({ attempts }: { attempts: MonitorAttempt[] }) {
  const max = Math.max(1, ...attempts.map(totalTokens));
  const measured = attempts.some((attempt) => attempt.usage.measured_calls > 0);
  return (
    <section className="monitor-panel">
      <h2>Tokens por interacción</h2>
      <p className="muted monitor-small">
        Entrada + salida de todas las llamadas de la interacción; las que abren hallazgo suman
        analizador y parcheador.
        {!measured && " El proveedor actual no es LIVE: las cifras no son consumo comercial."}
      </p>
      <div className="monitor-bars">
        {attempts.slice(-20).map((attempt) => (
          <div key={attempt.id} className={`monitor-bar tone-${outcomeOf(attempt).tone}`}>
            <span className="monitor-small">{attempt.id.slice(-6)}</span>
            <span className="monitor-track">
              <i style={{ width: `${(totalTokens(attempt) / max) * 100}%` }} />
            </span>
            <span className="monitor-n">{tokensText(attempt)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

export function MonitorTrends({ attempts }: { attempts: MonitorAttempt[] }) {
  return (
    <div className="monitor-bottom">
      <ViolationRate attempts={attempts} />
      <TokenBars attempts={attempts} />
    </div>
  );
}
