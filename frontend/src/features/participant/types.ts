export interface ArenaSession {
  id: string;
  alias: string;
  created_at: string;
  token: string;
  expires_at: string;
  customer_name: string;
  order_ids: string[];
  objectives: string[];
}

export interface Attempt {
  id: string;
  status: "queued" | "running" | "evaluated" | "inconclusive";
  outcome: "apparent_success" | "prevented" | "not_achieved" | "inconclusive" | null;
  policy_version: number;
  reply: string;
  created_at: string;
}
