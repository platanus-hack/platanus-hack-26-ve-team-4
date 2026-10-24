import type { ReplayGraph } from "../arena/replay/types";
import type { Evidence } from "../operator/api";

export type Outcome =
  | "confirmed_violation"
  | "prevented"
  | "not_achieved"
  | "contained_honeypot"
  | "inconclusive";

export interface Usage {
  calls: number;
  measured_calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface AttemptPatch {
  version: number;
  status: string;
  activated_at: string | null;
  replay: boolean;
}

/** Fila de `GET /api/operator/monitor` (backend: arena/monitor_view.py). */
export interface MonitorAttempt {
  id: string;
  created_at: string;
  updated_at: string;
  origin: string;
  status: string;
  outcome: Outcome | null;
  route: "protected" | "honeypot";
  policy_version: number;
  messages: string[];
  family: string | null;
  family_source: "campaign" | "analyzer" | null;
  finding_id: string | null;
  patch: AttemptPatch | null;
  duration_seconds: number | null;
  usage: Usage;
}

export interface Monitor {
  llm_mode: string;
  attempts: MonitorAttempt[];
  totals: Usage;
}

export interface AttemptDetail extends Evidence {
  graph: ReplayGraph;
}
