import { requestJson } from "../../shared/api/http";
import { saveSession } from "../participant/storage";
import type { ArenaSession } from "../participant/types";

// Prefijo reservado en backend/src/agent_zero/sessions/reserved_alias.py: solo se acepta con el
// secreto de operador, el tablero lo rotula «Prueba interna» y no cuenta en KPI ni clasificación.
export const TEST_PREFIX = "Interno-";

export function testAlias(name: string, suffix: string): string {
  const clean = name.trim().replace(/\s+/g, "-");
  return `${TEST_PREFIX}${clean || suffix}`.slice(0, 40);
}

export function createTestSession(secret: string, alias: string): Promise<ArenaSession> {
  return requestJson<ArenaSession>("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Operator-Secret": secret },
    body: JSON.stringify({ alias, accepted_rules: true }),
  });
}

// Deja la sesión como la pulsera del navegador y abre el chat del participante en otra pestaña.
export async function openTestChat(secret: string, alias: string): Promise<ArenaSession> {
  const session = await createTestSession(secret, alias);
  saveSession(session);
  window.open("/", "_blank", "noopener");
  return session;
}
