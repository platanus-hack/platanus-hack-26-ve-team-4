import type { Outcome } from "../monitor/types";

export type ChatKind = "audience" | "swarm" | "prober" | "test" | "replay";

export interface AuditRound {
  /** `null` para la ronda en curso; el id del archivo para las anteriores. */
  id: string | null;
  round_id: string;
  current: boolean;
  started_at: string;
  reason: string;
}

export interface Diversion {
  reason: string;
  at: string;
}

export interface ChatSummary {
  id: string;
  alias: string;
  kind: ChatKind;
  customer_id: string;
  route: "protected" | "honeypot";
  created_at: string;
  last_activity: string;
  attempts: number;
  conversations: number;
  outcomes: Partial<Record<Outcome, number>>;
  violations: number;
  diversion: Diversion | null;
  preview: string;
}

export interface ToolStep {
  event_id: number;
  kind: "tool_proposed" | "tool_denied" | "tool_completed" | "tool_failed";
  tool: string;
  arguments: Record<string, unknown>;
  provenance: Record<string, string>;
  validator: string;
  effect: Record<string, unknown>;
  output: Record<string, unknown>;
}

export interface Verdict {
  objective_id: string;
  violated: boolean;
  level?: string;
  detail?: string;
}

export interface AuditAttempt {
  id: string;
  position: number;
  created_at: string;
  updated_at: string;
  duration_seconds: number | null;
  status: string;
  outcome: Outcome | null;
  route: "protected" | "honeypot";
  policy_version: number;
  origin: string;
  objective_id: string | null;
  campaign_id: string | null;
  messages: string[];
  reply: string;
  verdicts: Verdict[];
  detail: string;
  tools: ToolStep[];
}

export interface ChatDetail extends ChatSummary {
  threads: { index: number; attempts: AuditAttempt[] }[];
}
