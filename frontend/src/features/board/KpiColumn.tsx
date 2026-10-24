import { formatDuration } from "../participant/RevealCard";
import type { LiveKpis } from "./types";

const number = new Intl.NumberFormat("es");

function Tile({
  title,
  value,
  context,
  n,
  source,
  note,
}: {
  title: string;
  value: string;
  context: string;
  n: number;
  source: string;
  note?: string;
}) {
  return (
    <section className="kpi" aria-label={title}>
      <h2 className="kpi-title">{title}</h2>
      <p className="kpi-value">{value}</p>
      <p className="kpi-context">{context}</p>
      {note && <p className="kpi-note">{note}</p>}
      <p className="kpi-source">
        n = {number.format(n)} · {source}
      </p>
    </section>
  );
}

export function KpiColumn({ kpis }: { kpis: LiveKpis }) {
  const { attacks, safe_space: safe, leaked, attacker_tokens: tokens, patches } = kpis;
  const objectives = Object.entries(leaked.by_objective)
    .map(([objective, count]) => `${objective} ${count}`)
    .join(" · ");
  return (
    <aside className="kpis" aria-label="Analíticas">
      <Tile
        title="Ataques"
        value={number.format(attacks.n)}
        context={`Público ${attacks.audience} · Agentes simulados ${attacks.swarm} · Prober ${attacks.prober}`}
        n={attacks.n}
        source="intentos de la ronda"
      />
      <Tile
        title="Espacio seguro"
        value={`${safe.diverted_sessions}/${safe.n}`}
        context={`sesiones llevadas al señuelo · ${safe.contained_attempts} intentos contenidos`}
        note={safe.label}
        n={safe.n}
        source="sesiones con alcance"
      />
      <Tile
        title="Ataques que dejamos pasar"
        value={String(leaked.leaked)}
        context={objectives ? `por objetivo: ${objectives}` : "violaciones confirmadas"}
        note={leaked.label}
        n={leaked.n}
        source="intentos con alcance"
      />
      <Tile
        title="Tokens que gasta el atacante"
        value={
          tokens.attacker.measured && tokens.attacker.tokens !== null
            ? number.format(tokens.attacker.tokens)
            : "No medido"
        }
        context={
          tokens.measured
            ? `${tokens.attacker.measured ? "" : "Tokens del atacante: no medido · "}Sostener el señuelo: ${
                tokens.decoy.measured && tokens.decoy.tokens !== null
                  ? `${number.format(tokens.decoy.tokens)} tokens`
                  : "no medido"
              }`
            : tokens.label
        }
        n={tokens.n}
        source="llamadas medidas en el ledger"
      />
      <Tile
        title="Parches que aprendió la defensa"
        value={String(patches.activated)}
        context={
          patches.median_seconds_to_patch === null
            ? `política vigente v${patches.current_version} · sin hallazgos cubiertos`
            : `política vigente v${patches.current_version} · mediana hallazgo a parche ${formatDuration(patches.median_seconds_to_patch)} sobre ${patches.findings_covered} hallazgos`
        }
        n={patches.n}
        source="versiones de política activadas"
      />
    </aside>
  );
}
