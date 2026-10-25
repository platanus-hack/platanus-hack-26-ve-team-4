import { testAlias } from "../operator/testSession";
import type { ArenaSession } from "../participant/types";

// Clave propia: la consola nunca lee ni escribe la pulsera del participante (agent-zero:participant:v1).
const CURRENT_KEY = "agent-zero:consola:v1";
const PAST_KEY = "agent-zero:consola:past:v1";
const MAX_PAST = 20;

// Prefijo del alias interno; testAlias le antepone «Interno-» y lo recorta a 40 caracteres.
export const CONSOLE_PREFIX = "consola";

export interface PastSession {
  id: string;
  alias: string;
  created_at: string;
}

// Mismo criterio que participant/storage.ts: si el almacenamiento falla, no se lanza nada.
function read<T>(key: string): T | null {
  try {
    return JSON.parse(localStorage.getItem(key) ?? "null") as T | null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Modo privado o cuota llena: la consola sigue funcionando sin recordar la sesión.
  }
}

function isSession(value: ArenaSession | null): value is ArenaSession {
  return Boolean(
    value &&
      typeof value.id === "string" &&
      typeof value.token === "string" &&
      typeof value.alias === "string" &&
      typeof value.customer_name === "string" &&
      typeof value.expires_at === "string" &&
      Array.isArray(value.order_ids) &&
      value.order_ids.every((id) => typeof id === "string") &&
      Array.isArray(value.objectives),
  );
}

function isPastSession(value: unknown): value is PastSession {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return (
    typeof item.id === "string" &&
    typeof item.alias === "string" &&
    typeof item.created_at === "string"
  );
}

export function consoleAlias(suffix: string): string {
  return testAlias(`${CONSOLE_PREFIX}-${suffix}`, suffix);
}

export function loadConsoleSession(): ArenaSession | null {
  const value = read<ArenaSession>(CURRENT_KEY);
  if (!isSession(value)) return null;
  if (Date.parse(value.expires_at) <= Date.now()) {
    // Solo se quita el puntero a la sesión vencida. El historial local (agent-zero:history:<id>)
    // no se borra: la auditoría sigue pudiendo consultar esa sesión.
    write(CURRENT_KEY, null);
    return null;
  }
  return value;
}

export function saveConsoleSession(session: ArenaSession | null) {
  write(CURRENT_KEY, session);
}

export function loadPastSessions(): PastSession[] {
  const value = read<unknown>(PAST_KEY);
  if (!Array.isArray(value)) return [];
  return value.filter(isPastSession).slice(0, MAX_PAST);
}

// Nota de diseño: archivar NO borra el historial local por id (agent-zero:history:<id>).
// Así la sesión anterior sigue consultable en la auditoría aunque ya no sea la actual.
export function archiveSession(session: ArenaSession) {
  const past = loadPastSessions();
  if (past.some((item) => item.id === session.id)) return;
  const entry: PastSession = {
    id: session.id,
    alias: session.alias,
    created_at: session.created_at,
  };
  write(PAST_KEY, [entry, ...past].slice(0, MAX_PAST));
}
