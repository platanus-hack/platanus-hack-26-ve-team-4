import { type ReactNode, useEffect, useRef, useState } from "react";
import type { LiveKpis } from "./types";

const integer = new Intl.NumberFormat("es-CL");
const OBJECTIVES = ["OBJ-ORDER", "OBJ-MEMORY", "OBJ-REFUND"];
const EVENT_MS = 4000;

/** Resalta el tile 4 s cuando su cifra principal cambia (no en la primera carga). */
function useBump(value: string): boolean {
  const previous = useRef(value);
  const [on, setOn] = useState(false);
  useEffect(() => {
    if (previous.current === value) return;
    previous.current = value;
    setOn(true);
    const timer = setTimeout(() => setOn(false), EVENT_MS);
    return () => clearTimeout(timer);
  }, [value]);
  return on;
}

function Tile({
  kind,
  label,
  value,
  children,
  context,
}: {
  kind: string;
  label: string;
  value: string;
  children: ReactNode;
  context: ReactNode;
}) {
  const bump = useBump(value);
  return (
    <article className={`av-tile ${kind}${bump ? " evt" : ""}`} aria-label={label}>
      <h2 className="av-k-label">{label}</h2>
      <div className="av-k-body">{children}</div>
      <p className="av-k-ctx">{context}</p>
    </article>
  );
}

const Row = ({ label, value, dot }: { label: string; value: string; dot?: string }) => (
  <div className="av-k-row">
    <span>
      {dot && <i className={`av-kd ${dot}`} />}
      {label}
    </span>
    <b>{value}</b>
  </div>
);

export function formatSeconds(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return rest ? `${minutes} min ${rest} s` : `${minutes} min`;
}

const thousands = (tokens: number) =>
  (tokens / 1000).toLocaleString("es-CL", { maximumFractionDigits: 1, minimumFractionDigits: 1 });

/**
 * Los 5 KPI de la maqueta. Todas las cifras y sus bases ({k, n}, alcance) vienen del servidor;
 * aquí solo se formatean.
 */
export function KpiColumn({ kpis, sessionsTotal }: { kpis: LiveKpis; sessionsTotal: number }) {
  const { attacks, safe_space: safe, leaked, attacker_tokens: tokens, patches } = kpis;
  const withoutAudience = (scope: string) => (scope === "swarm_prober" ? " sin Público" : "");
  const most = Math.max(1, ...OBJECTIVES.map((o) => leaked.by_objective[o] ?? 0));
  const percent = safe.n > 0 ? `${Math.round((safe.safe_sessions / safe.n) * 100)} %` : "—";
  const attackerTokens = tokens.attacker.measured ? tokens.attacker.tokens : null;
  const decoyTokens = tokens.decoy.measured ? tokens.decoy.tokens : null;
  return (
    <aside className="av-kpis" aria-label="Analíticas">
      <Tile
        kind="t-att"
        label="Intentos"
        value={String(attacks.n)}
        context={`n = ${integer.format(attacks.n)} intentos · ${sessionsTotal} sesiones${
          attacks.in_flight ? ` · ${attacks.in_flight} en curso` : ""
        }`}
      >
        <div className="av-k-num">{integer.format(attacks.n)}</div>
        <div className="av-k-side">
          <Row dot="aud" label="Público" value={integer.format(attacks.audience)} />
          <Row dot="sim" label="Agentes simulados" value={integer.format(attacks.swarm)} />
          <Row dot="pro" label="Prober" value={integer.format(attacks.prober)} />
        </div>
      </Tile>

      <Tile
        kind="t-safe"
        label="Espacio seguro"
        value={`${safe.safe_sessions}/${safe.n}/${safe.contained_attempts}`}
        context={`en señuelo · fuente: enrutador${withoutAudience(safe.scope)}`}
      >
        <div className="av-k-num">
          {safe.safe_sessions}
          <small>/{safe.n}</small>
        </div>
        <div className="av-k-side">
          <Row label="Intentos contenidos" value={integer.format(safe.contained_attempts)} />
          <Row label="De las sesiones" value={percent} />
        </div>
      </Tile>

      <Tile
        kind="t-leak"
        label="Ataques que dejamos pasar"
        value={`${leaked.leaked}/${leaked.n}`}
        context={`de ${integer.format(leaked.n)}${withoutAudience(leaked.scope)} · Σ ${leaked.objective_sum} obj. (se solapan)`}
      >
        <div className="av-k-num">{integer.format(leaked.leaked)}</div>
        <div className="av-k-side">
          {OBJECTIVES.map((objective) => {
            const count = leaked.by_objective[objective] ?? 0;
            return (
              <div className="av-k-row obj" key={objective}>
                <span>{objective}</span>
                <span className="av-bar">
                  <i style={{ width: `${(count / most) * 100}%` }} />
                </span>
                <b>{count}</b>
              </div>
            );
          })}
        </div>
      </Tile>

      <Tile
        kind="t-tok"
        label="Tokens: atacante y señuelo"
        value={`${attackerTokens ?? "-"}/${decoyTokens ?? "-"}`}
        context={
          tokens.measured
            ? `n = ${integer.format(tokens.n)} llamadas · señuelo: nuestro`
            : `n = ${integer.format(attacks.prober)} Prober · sin medir`
        }
      >
        {tokens.measured ? (
          <>
            <div className="av-k-num">
              {attackerTokens === null ? "—" : thousands(attackerTokens)}
              {attackerTokens !== null && <small>k</small>}
            </div>
            <div className="av-k-side">
              <Row
                label="Prober"
                value={attackerTokens === null ? "no medido" : integer.format(attackerTokens)}
              />
              <Row
                label="Señuelo"
                value={decoyTokens === null ? "no medido" : integer.format(decoyTokens)}
              />
            </div>
          </>
        ) : (
          <>
            <div className="av-k-num nm">—</div>
            <div className="av-k-side av-k-nm">
              <b className="av-k-nm-t">No medido</b>
              <span className="av-k-nm-s" aria-hidden="true">
                {tokens.label === "no medido en modo demo" ? "(modo demo)" : tokens.label}
              </span>
              <span className="av-sr">{tokens.label}</span>
            </div>
          </>
        )}
      </Tile>

      <Tile
        kind="t-pat"
        label="Parches que aprendió la defensa"
        value={`${patches.activated}/${patches.current_version}`}
        context={`n = ${patches.findings_total} hallazgos · ${patches.findings_covered} cubiertos · mediana`}
      >
        <div className="av-k-num">{integer.format(patches.activated)}</div>
        <div className="av-k-side">
          <Row label="Versión vigente" value={`v${patches.current_version}`} />
          <Row label="Hallazgo → parche" value={formatSeconds(patches.median_seconds_to_patch)} />
        </div>
      </Tile>
    </aside>
  );
}
