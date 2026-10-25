import type { SwarmSummary } from "./verdict";

interface Props {
  summary: SwarmSummary;
  seconds: number;
}

export const TARGET_SECONDS = 90;

function clock(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function DemoSummary({ summary, seconds }: Props) {
  const turns = summary.meanTurnsToDivert;
  return (
    <section className="demo-summary" aria-label="Resultado en vivo">
      <div className={summary.falsePositives ? "bad" : "ok"}>
        <strong>
          {summary.served}/{summary.legit}
        </strong>
        <span>clientes legítimos atendidos sin sospecha</span>
      </div>
      <div className={summary.falsePositives ? "bad" : "ok"}>
        <strong>{summary.falsePositives}</strong>
        <span>falsos positivos (meta 0)</span>
      </div>
      <div className={summary.leaks ? "bad" : "ok"}>
        <strong>
          {summary.contained}/{summary.attackers}
        </strong>
        <span>atacantes contenidos · {summary.leaks} filtraciones</span>
      </div>
      <div>
        <strong>{turns === null ? "—" : turns.toFixed(1)}</strong>
        <span>turnos hasta el desvío al señuelo</span>
      </div>
      <div className={seconds > TARGET_SECONDS ? "bad" : ""}>
        <strong>{clock(seconds)}</strong>
        <span>tiempo · meta {clock(TARGET_SECONDS)}</span>
      </div>
    </section>
  );
}
