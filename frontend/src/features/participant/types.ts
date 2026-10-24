import type { AttemptStatus, PublicOutcome } from "../../shared/attemptLabels";

export interface ArenaSession {
  id: string;
  alias: string;
  created_at: string;
  token: string;
  expires_at: string;
}

export interface Attempt {
  id: string;
  status: AttemptStatus;
  outcome: PublicOutcome | null;
  messages: string[];
  reply: string | null;
  created_at: string;
  updated_at: string;
}
