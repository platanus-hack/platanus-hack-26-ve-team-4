import type { CoevolutionRound } from "./types";

const WIDTH = 520;
const HEIGHT = 220;
const LEFT = 44;
const RIGHT = 16;
const TOP = 16;
const BOTTOM = 40;

function y(rate: number) {
  return TOP + (1 - rate) * (HEIGHT - TOP - BOTTOM);
}

export function CoevolutionPlot({ rounds }: { rounds: CoevolutionRound[] }) {
  const step = (WIDTH - LEFT - RIGHT) / Math.max(rounds.length, 1);
  const x = (index: number) => LEFT + step * (index + 0.5);
  const path = rounds
    .map((round, index) => ({ round, index }))
    .filter(({ round }) => round.success_rate !== null)
    .map(
      ({ round, index }, order) =>
        `${order === 0 ? "M" : "L"}${x(index)},${y(round.success_rate ?? 0)}`,
    )
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label="Tasa de éxito del ataque por versión de política"
      className="coevolution-plot"
    >
      {[0, 0.5, 1].map((tick) => (
        <g key={tick}>
          <line x1={LEFT} x2={WIDTH - RIGHT} y1={y(tick)} y2={y(tick)} className="coevo-grid" />
          <text x={LEFT - 8} y={y(tick) + 4} textAnchor="end" className="coevo-label">
            {Math.round(tick * 100)}%
          </text>
        </g>
      ))}
      <path d={path} className="coevo-line" fill="none" />
      {rounds.map((round, index) => (
        <g key={round.version}>
          {round.ci_low !== null && round.ci_high !== null && (
            <line
              x1={x(index)}
              x2={x(index)}
              y1={y(round.ci_low)}
              y2={y(round.ci_high)}
              className="coevo-ci"
            />
          )}
          {round.success_rate !== null && (
            <circle cx={x(index)} cy={y(round.success_rate)} r={5} className="coevo-dot" />
          )}
          <text x={x(index)} y={HEIGHT - 22} textAnchor="middle" className="coevo-label">
            v{round.version}
          </text>
          <text x={x(index)} y={HEIGHT - 6} textAnchor="middle" className="coevo-label">
            n={round.evaluable}
            {round.inconclusive > 0 ? ` +${round.inconclusive} inc.` : ""}
          </text>
        </g>
      ))}
    </svg>
  );
}
