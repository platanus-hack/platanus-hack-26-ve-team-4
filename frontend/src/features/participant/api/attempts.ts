import { getJson, postJson } from "../../../shared/api/http";
import type { ArenaSession, Attempt } from "../types";

export type SessionProfile = Pick<ArenaSession, "id" | "alias" | "created_at">;

export function getMe(token: string): Promise<SessionProfile> {
  return getJson<SessionProfile>("/api/sessions/me", { token });
}

export function listAttempts(token: string): Promise<Attempt[]> {
  return getJson<Attempt[]>("/api/attempts", { token });
}

export function submitAttempt(
  token: string,
  messages: string[],
  idempotencyKey: string,
): Promise<Attempt> {
  return postJson<Attempt>(
    "/api/attempts",
    { messages, idempotency_key: idempotencyKey },
    { token },
  );
}
