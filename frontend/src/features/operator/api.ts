import { requestJson } from "../../shared/api/http";

export interface Policy {
  version: number;
  parent_version?: number | null;
  status: string;
  rules: string[];
  reason: string;
  finding_ids?: string[];
  content_hash?: string;
  analysis?: {
    status: string;
    advisory: boolean;
    error: string;
    explanation?: {
      rationale: string;
      expected_effect: string;
      regression_risks: string[];
      limitations: string;
    };
  } | null;
  validation: {
    passed?: boolean;
    level1_passed?: boolean;
    reason?: string;
    cases?: { name: string; passed: boolean; error?: string | null }[];
  };
}
export interface Finding {
  id: string;
  objective_id: string;
  status: string;
  probable_cause: string;
  attempt_ids: string[];
  analysis?: {
    status: string;
    attack_family?: string;
    probable_cause?: string;
    reproduction_steps?: string[];
    limitations?: string;
    error?: string;
  } | null;
}
export interface OperatorAttempt {
  id: string;
  status: string;
  outcome: string | null;
  route: string;
  policy_version: number;
  reply: string;
  origin?: string;
  messages?: string[];
  created_at?: string;
}
export interface Evidence extends OperatorAttempt {
  assessment?: {
    verdicts?: {
      objective_id: string;
      violated: boolean;
      evidence_event_ids?: number[];
      detail?: string;
      level?: string;
    }[];
    [key: string]: unknown;
  };
  events?: { id: number; type: string; timestamp: string; data: Record<string, unknown> }[];
}
export interface Campaign {
  id: string;
  status: string;
  max_attempts: number;
  attempt_ids: string[];
  generation?: string;
  generation_calls?: number;
  stop_reason?: string | null;
  cases?: {
    index: number;
    status: string;
    attempt_id: string | null;
    digest: string;
    error: string;
    case: { family?: string; surface?: string; messages?: string[] };
  }[];
}
export interface EvaluationVersion {
  adversarial: {
    total: number;
    evaluable: number;
    confirmed_violations: number;
    inconclusive: number;
    violation_rate: number | null;
    conservative_rate: number | null;
  };
  legitimate: {
    total: number;
    evaluable: number;
    correct: number;
    inconclusive: number;
    utility_rate: number | null;
    incorrect_block_rate: number | null;
  };
}
export interface Evaluation {
  id: string;
  status: string;
  before_version: number;
  after_version: number;
  repetitions: number;
  total: number;
  completed: number;
  created_at: string;
  report: {
    versions?: Record<string, EvaluationVersion>;
    mode?: string;
    limitations?: string[];
    [key: string]: unknown;
  };
}
export function operatorRequest<T>(
  secret: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  return requestJson<T>(`/api/operator${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", "X-Operator-Secret": secret },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    signal,
  });
}
