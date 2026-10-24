export type NodeKind = "agent" | "tool" | "effect";
export type NodeState = "ok" | "effect" | "prevented";
export type EdgeState = "ok" | "effect" | "blocked";

export interface ReplayNode {
  id: string;
  kind: NodeKind;
  label: string;
  state?: NodeState;
  effect?: string;
}

export interface ReplayEdge {
  from: string;
  to: string;
  state: EdgeState;
  control?: string;
}

export interface ReplayGraph {
  nodes: ReplayNode[];
  edges: ReplayEdge[];
}

export interface ReplaySide {
  version: number;
  graph: ReplayGraph;
}

export interface LegitRow {
  name: string;
  passed: boolean;
  tool: string | null;
}

export interface Replay {
  version: number;
  source: string;
  before: ReplaySide;
  after: ReplaySide;
  legit: LegitRow[];
}
