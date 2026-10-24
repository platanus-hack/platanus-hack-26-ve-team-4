import type { ReplayEdge, ReplayGraph, ReplayNode } from "./types";
import "./replay.css";

const ROW = 64;
const WIDTH = 360;
const COLUMNS = { agent: { x: 4, w: 80 }, tool: { x: 118, w: 100 }, effect: { x: 250, w: 106 } };
const LINE = 13;

export function wrap(label: string, max: number): string[] {
  const lines: string[] = [];
  for (const token of label.match(/[^ _]+[ _]?/g) ?? [label]) {
    const last = lines.at(-1);
    if (last !== undefined && last.length + token.length <= max)
      lines[lines.length - 1] = last + token;
    else lines.push(token);
  }
  return lines.map((line) => line.trimEnd());
}

function status(node: ReplayNode, cut: boolean): string | null {
  if (node.kind !== "effect") return null;
  return node.state === "prevented" && cut ? "bloqueado" : "efecto indebido";
}

function Node({
  node,
  y,
  index,
  cut,
}: {
  node: ReplayNode;
  y: number;
  index: number;
  cut: boolean;
}) {
  const column = COLUMNS[node.kind];
  const lines = wrap(node.label, node.kind === "agent" ? 11 : 15);
  const note = status(node, cut);
  const rows = lines.length + (note ? 1 : 0);
  const height = rows * LINE + 12;
  const stateClass =
    node.kind === "effect" ? (note === "bloqueado" ? "prevented" : "effect") : "ok";
  return (
    <g
      className={`replay-node replay-node--${stateClass}`}
      style={{ animationDelay: `${index * 0.3}s` }}
      data-node={node.id}
    >
      <rect x={column.x} y={y - height / 2} width={column.w} height={height} rx={6} />
      {lines.map((line, row) => (
        <text
          key={line}
          x={column.x + column.w / 2}
          y={y - height / 2 + 6 + (row + 1) * LINE - 3}
          textAnchor="middle"
        >
          {line}
        </text>
      ))}
      {note && (
        <text
          className="replay-note"
          x={column.x + column.w / 2}
          y={y - height / 2 + 6 + rows * LINE - 3}
          textAnchor="middle"
        >
          {note}
        </text>
      )}
    </g>
  );
}

function Edge({ edge, y1, y2, cut }: { edge: ReplayEdge; y1: number; y2: number; cut: boolean }) {
  const toEffect = edge.to.startsWith("effect");
  const from = toEffect ? COLUMNS.tool : COLUMNS.agent;
  const to = toEffect ? COLUMNS.effect : COLUMNS.tool;
  const x1 = from.x + from.w;
  const state = edge.state === "blocked" && !cut ? "effect" : edge.state;
  const middle = (x1 + to.x) / 2;
  return (
    <g className={`replay-edge replay-edge--${state}`} data-edge={`${edge.from}>${edge.to}`}>
      <line x1={x1} y1={y1} x2={to.x} y2={y2} />
      {state === "blocked" && (
        <path className="replay-flash" d={`M${middle - 6} ${y2 - 6}l12 12m0-12l-12 12`} />
      )}
    </g>
  );
}

export function AttackGraph({
  graph,
  version,
  cut,
}: {
  graph: ReplayGraph;
  version: number;
  cut: boolean;
}) {
  const agent = graph.nodes.find((node) => node.kind === "agent");
  const tools = graph.nodes.filter((node) => node.kind === "tool");
  const positions = new Map<string, number>();
  tools.forEach((tool, row) => {
    positions.set(tool.id, ROW / 2 + row * ROW);
    positions.set(`effect-${tool.id.split("-")[1]}`, ROW / 2 + row * ROW);
  });
  const height = Math.max(1, tools.length) * ROW;
  const summary = graph.edges.some((edge) => edge.state === "blocked" && cut)
    ? `Política v${version}: el ataque queda bloqueado antes del efecto.`
    : `Política v${version}: el ataque llega al efecto indebido.`;
  return (
    <svg
      className="replay-graph"
      viewBox={`0 0 ${WIDTH} ${height}`}
      role="img"
      aria-label={summary}
    >
      <title>{summary}</title>
      {agent && <Node node={agent} y={height / 2} index={0} cut={cut} />}
      {graph.edges.map((edge) => (
        <Edge
          key={`${edge.from}-${edge.to}`}
          edge={edge}
          y1={edge.from === "agent" ? height / 2 : (positions.get(edge.from) ?? 0)}
          y2={positions.get(edge.to) ?? 0}
          cut={cut}
        />
      ))}
      {graph.nodes
        .filter((node) => node.kind !== "agent")
        .map((node, index) => (
          <Node
            key={node.id}
            node={node}
            y={positions.get(node.id) ?? 0}
            index={index + 1}
            cut={cut}
          />
        ))}
    </svg>
  );
}
