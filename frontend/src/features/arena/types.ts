export type EventType =
  | "attempt_queued"
  | "attempt_started"
  | "attempt_completed"
  | "tool_proposed"
  | "tool_denied"
  | "tool_completed"
  | "route_changed"
  | "attempt_evaluated"
  | "finding_opened"
  | "patch_proposed"
  | "patch_validated"
  | "policy_activated"
  | "policy_rolled_back";

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

export interface ArenaState {
  accepting: boolean;
  revealed: boolean;
  provisional: boolean;
  policy_version: number;
  attempts: number;
  scores: { alias: string; score: number }[];
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
