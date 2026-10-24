import { requestJson } from "../../shared/api/http";

export interface Policy {
  version: number;
  status: string;
  rules: string[];
  reason: string;
  validation: {
    passed?: boolean;
    level1_passed?: boolean;
    cases?: { name: string; passed: boolean }[];
  };
}

export interface Finding {
  id: string;
  objective_id: string;
  status: string;
  probable_cause: string;
  attempt_ids: string[];
}

export interface OperatorAttempt {
  id: string;
  status: string;
  outcome: string | null;
  route: string;
  policy_version: number;
  reply: string;
}

export interface Campaign {
  id: string;
  status: string;
  attempt_ids: string[];
}

export function operatorRequest<T>(secret: string, path: string, body?: unknown): Promise<T> {
  return requestJson<T>(`/api/operator${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", "X-Operator-Secret": secret },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}
