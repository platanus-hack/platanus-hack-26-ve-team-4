export interface ArenaSession {
  id: string;
  alias: string;
  created_at: string;
  token: string;
  expires_at: string;
  customer_name: string;
  order_ids: string[];
  objectives: string[];
  round_id?: string;
  attempts_per_minute?: number;
  limits?: { attempts_per_minute: number; max_messages: number; message_max_length: number };
}

export interface Attempt {
  id: string;
  status: "queued" | "running" | "evaluated" | "inconclusive";
  outcome:
    | "apparent_success"
    | "confirmed_violation"
    | "contained_honeypot"
    | "prevented"
    | "not_achieved"
    | "inconclusive"
    | null;
  policy_version: number;
  reply: string;
  created_at: string;
  messages?: string[];
  idempotency_key?: string;
  // Intento previo cuya conversación continúa este (lo arma el servidor).
  continues?: string | null;
}

export interface ConversationEntry {
  key: string;
  messages: string[];
  // Mensajes del lote tal como se escribieron; `messages` es lo que viajó al servidor.
  parts?: string[];
  attempt: Attempt | null;
  continues?: string | null;
}

export interface DecoyReveal {
  retained_seconds: number;
  post_diversion_steps: number;
  post_diversion_attempts: number;
  honeytools_touched: string[];
  credential_issued: boolean;
  token_reused: boolean;
}
