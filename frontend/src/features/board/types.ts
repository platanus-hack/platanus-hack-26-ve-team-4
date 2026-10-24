export type SessionKind = "audience" | "swarm" | "prober";
export type KpiScope = "all" | "swarm_prober";

export interface LiveAttempt {
  id: string;
  status: string;
  outcome: string | null;
  route: string | null;
  messages: string[];
  reply: string;
  created_at: string;
}

export interface LiveSession {
  session_id: string;
  alias: string;
  kind: SessionKind;
  route: string | null;
  customer_id: string;
  last_activity: string;
  attempt_total: number;
  attempts: LiveAttempt[];
}

export interface TokenPart {
  measured: boolean;
  tokens: number | null;
  calls: number;
}

export interface LiveKpis {
  attacks: {
    n: number;
    audience: number;
    swarm: number;
    prober: number;
    source: string;
  };
  safe_space: {
    n: number;
    diverted_sessions: number;
    contained_attempts: number;
    scope: KpiScope;
    label: string;
    source: string;
  };
  leaked: {
    n: number;
    leaked: number;
    by_objective: Record<string, number>;
    scope: KpiScope;
    label: string;
    source: string;
  };
  attacker_tokens: {
    measured: boolean;
    label: string;
    attacker: TokenPart;
    decoy: TokenPart;
    n: number;
    source: string;
  };
  patches: {
    n: number;
    activated: number;
    current_version: number;
    median_seconds_to_patch: number | null;
    findings_covered: number;
    source: string;
  };
}

export interface LiveBoard {
  revealed: boolean;
  llm_mode: string;
  policy_version: number;
  sessions: LiveSession[];
  kpis: LiveKpis;
  generated_at: string;
}
