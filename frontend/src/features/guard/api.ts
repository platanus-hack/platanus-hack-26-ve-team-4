import { requestJson } from "../../shared/api/http";

export type PolicyStatus = "active" | "proposed" | "superseded" | "rolled_back" | "rejected";

export interface ContractSummary {
  contract_id: string;
  version: string;
  name: string;
  digest: string;
  tools: string[];
  invariants: string[];
  legitimate: number;
  auto_activate: boolean;
  source?: "file" | "api";
}

export interface GateReport {
  accepted: boolean;
  original_blocked: number;
  original_total: number;
  legitimate_kept: number;
  legitimate_total: number;
  injected_blocked: number;
  injected_total: number;
}

export interface GuardRule {
  rule_id: string;
  tool: string;
  reason: string;
  text: string;
  deny_when: { kind: string; argument: string; [key: string]: unknown };
}

export interface GuardPolicy {
  version: number;
  parent_version: number | null;
  status: PolicyStatus;
  rules: GuardRule[];
  report: {
    llm_mode?: string;
    source?: string;
    violated?: string[];
    gate?: GateReport;
    [key: string]: unknown;
  };
  finding_id: string | null;
  contract_digest: string;
  created_at: string;
}

export interface GuardFinding {
  id: string;
  call_id: string;
  invariant_ids: string[];
  policy_version: number;
  resolved_by: number | null;
  created_at: string;
}

export type ValidationResult =
  | { valid: true; contract: ContractSummary }
  | { valid: false; error: string };

export function guardRequest<T>(
  secret: string,
  path: string,
  options: { method?: "GET" | "POST"; yaml?: string; signal?: AbortSignal } = {},
): Promise<T> {
  const { method = "GET", yaml, signal } = options;
  return requestJson<T>(`/api/guard${path}`, {
    method: yaml === undefined ? method : "POST",
    headers: {
      "X-Operator-Secret": secret,
      ...(yaml === undefined ? {} : { "Content-Type": "text/yaml" }),
    },
    ...(yaml === undefined ? {} : { body: yaml }),
    signal,
  });
}

export const contractPath = (id: string) => `/${encodeURIComponent(id)}`;
