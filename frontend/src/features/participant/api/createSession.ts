import { postJson } from "../../../shared/api/http";
import type { ArenaSession } from "../types";

export function createSession(alias: string): Promise<ArenaSession> {
  return postJson<ArenaSession>("/api/sessions", { alias });
}
