export type EventType =
  | "attempt_queued"
  | "attempt_started"
  | "attempt_completed"
  | "tool_proposed"
  | "tool_denied"
  | "tool_completed"
  | "tool_failed"
  | "route_changed"
  | "attempt_evaluated"
  | "finding_opened"
  | "patch_proposed"
  | "patch_validated"
  | "policy_activated"
  | "policy_rolled_back"
  | "probe_round_closed";

export interface CoevolutionRound {
  version: number;
  queries: number;
  evaluable: number;
  inconclusive: number;
  pending: number;
  violations: number;
  success_rate: number | null;
  ci_low: number | null;
  ci_high: number | null;
  queries_to_break: number | null;
  censored: boolean;
  first_break: { mutator: string; family: string | null } | null;
}

export interface CoevolutionResponse {
  budget: number;
  evidence_mode: string;
  status: string | null;
  versions: CoevolutionRound[];
  summary: { baseline: CoevolutionRound; latest: CoevolutionRound } | null;
}

export interface TraceEvent {
  id: number;
  type: EventType;
  visibility: "public" | "operator";
  attempt_id: string | null;
  session_id: string | null;
  policy_version: number | null;
  timestamp: string;
  data: Record<string, unknown>;
}

export type ConnectionState = "connecting" | "open" | "reconnecting";

export interface ScoreRow {
  alias: string;
  score: number;
  // Only after the reveal: points that looked real and points that stayed in the honeypot.
  apparent?: number;
  contained?: number;
}

export interface ArenaState {
  accepting: boolean;
  revealed: boolean;
  provisional: boolean;
  policy_version: number;
  attempts: number;
  scores: ScoreRow[];
  // Only after the reveal: attempts that looked successful, split by where they happened.
  confirmed_violations?: number;
  contained_honeypot?: number;
  round_id?: string;
  started_at?: string;
  session_count?: number;
  session_limit?: number;
  audience_attempts?: number;
  autonomous_attempts?: number;
  queued_attempts?: number;
  running_attempts?: number;
  evaluated_attempts?: number;
  inconclusive_attempts?: number;
  prevented_attempts?: number;
  open_findings?: number;
  llm_mode?: string;
  evidence_mode?: string;
}
