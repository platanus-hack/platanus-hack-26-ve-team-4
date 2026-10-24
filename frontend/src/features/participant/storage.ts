import type { ArenaSession, ConversationEntry } from "./types";

const SESSION_KEY = "agent-zero:participant:v1";
const historyKey = (id: string) => `agent-zero:history:${id}`;

// localStorage, no sessionStorage: la pulsera sobrevive a cerrar la pestaña y la comparten las
// pestañas del navegador, así que volver no crea otra sesión ni gasta cupo de la ronda.
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
    // Private browsing/storage limits must not make an accepted attempt look failed.
  }
}
// Pulseras guardadas por versiones anteriores en sessionStorage: se mueven una vez.
function migrateFromTab() {
  try {
    const legacy = sessionStorage.getItem(SESSION_KEY);
    if (legacy !== null && localStorage.getItem(SESSION_KEY) === null) {
      localStorage.setItem(SESSION_KEY, legacy);
    }
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // Sin almacenamiento disponible no hay nada que migrar.
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
export function loadSession(): ArenaSession | null {
  migrateFromTab();
  const value = read<ArenaSession>(SESSION_KEY);
  if (!isSession(value)) {
    return null;
  }
  if (Date.parse(value.expires_at) <= Date.now()) {
    saveSession(null);
    return null;
  }
  return value;
}
export function saveSession(session: ArenaSession | null) {
  const previous = read<ArenaSession>(SESSION_KEY);
  if (session === null && previous && typeof previous.id === "string") {
    write(historyKey(previous.id), null);
  }
  write(SESSION_KEY, session);
}
export function loadHistory(id: string): ConversationEntry[] {
  const value = read<ConversationEntry[]>(historyKey(id));
  return Array.isArray(value)
    ? value.filter(
        (entry) =>
          entry &&
          typeof entry.key === "string" &&
          Array.isArray(entry.messages) &&
          entry.messages.every((message) => typeof message === "string") &&
          (entry.attempt === null ||
            (entry.attempt &&
              typeof entry.attempt.id === "string" &&
              typeof entry.attempt.reply === "string" &&
              typeof entry.attempt.policy_version === "number" &&
              ["queued", "running", "evaluated", "inconclusive"].includes(entry.attempt.status))),
      )
    : [];
}
export function saveHistory(id: string, entries: ConversationEntry[]) {
  write(historyKey(id), entries);
}
