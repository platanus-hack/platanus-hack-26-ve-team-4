export type EventType =
  | "attempt_queued"
  | "attempt_started"
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
