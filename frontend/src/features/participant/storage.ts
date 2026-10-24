import type { ArenaSession, ConversationEntry } from "./types";

const SESSION_KEY = "agent-zero:participant:v1";
const historyKey = (id: string) => `agent-zero:history:${id}`;

function read<T>(key: string): T | null {
  try {
    return JSON.parse(sessionStorage.getItem(key) ?? "null") as T | null;
  } catch {
    return null;
  }
}
function write(key: string, value: unknown) {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Private browsing/storage limits must not make an accepted attempt look failed.
  }
}
export function loadSession(): ArenaSession | null {
  const value = read<ArenaSession>(SESSION_KEY);
  return value &&
    typeof value.id === "string" &&
    typeof value.token === "string" &&
    typeof value.alias === "string" &&
    typeof value.customer_name === "string" &&
    typeof value.expires_at === "string" &&
    Array.isArray(value.order_ids) &&
    value.order_ids.every((id) => typeof id === "string") &&
    Array.isArray(value.objectives)
    ? value
    : null;
}
export function saveSession(session: ArenaSession | null) {
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
