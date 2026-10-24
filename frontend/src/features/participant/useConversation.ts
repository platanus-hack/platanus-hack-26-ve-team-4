import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, errorMessage, isUnauthorized, requestJson } from "../../shared/api/http";
import { usePolling } from "../../shared/api/usePolling";
import { loadHistory, saveHistory } from "./storage";
import type { ArenaSession, Attempt, ConversationEntry } from "./types";

// Igual que attempts/conversation.py: intentos que puede tener una conversación.
export const MAX_THREAD = 6;

export const active = (attempt: Attempt | null) =>
  !attempt || attempt.status === "queued" || attempt.status === "running";

export function mergeHistory(local: ConversationEntry[], remote: Attempt[]): ConversationEntry[] {
  const entries = [...local];
  for (const attempt of remote) {
    const index = entries.findIndex(
      (entry) => entry.attempt?.id === attempt.id || entry.key === attempt.idempotency_key,
    );
    const previous = index >= 0 ? entries[index] : undefined;
    const entry = {
      key: previous?.key ?? attempt.idempotency_key ?? attempt.id,
      messages: attempt.messages ?? previous?.messages ?? [],
      attempt:
        previous?.attempt && !active(previous.attempt) && active(attempt)
          ? previous.attempt
          : attempt,
      continues: attempt.continues ?? previous?.continues ?? null,
    };
    if (index >= 0) entries[index] = entry;
    else entries.push(entry);
  }
  return entries;
}

/** Conversaciones: un intento sin `continues` empieza una nueva. */
export function threadsOf(entries: ConversationEntry[]): ConversationEntry[][] {
  const threads: ConversationEntry[][] = [];
  for (const entry of entries) {
    const last = threads.at(-1);
    if (!entry.continues || !last) threads.push([entry]);
    else last.push(entry);
  }
  return threads;
}

function newKey() {
  // getRandomValues also works on a phone visiting a local HTTP address, where
  // randomUUID is unavailable outside a secure context.
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

export function useConversation(session: ArenaSession, onExpired?: () => void) {
  const [entries, setEntries] = useState<ConversationEntry[]>(() => loadHistory(session.id));
  const [fresh, setFresh] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restored, setRestored] = useState<string | null>(null);
  const [retryAt, setRetryAt] = useState(0);
  const [now, setNow] = useState(Date.now);
  const submitting = useRef(false);
  const mounted = useRef(true);
  const load = useCallback(
    (signal: AbortSignal) =>
      requestJson<Attempt[]>("/api/attempts", {
        headers: { Authorization: `Bearer ${session.token}` },
        signal,
      }),
    [session.token],
  );
  const history = usePolling(load, 1500);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => saveHistory(session.id, entries), [session.id, entries]);
  useEffect(() => {
    if (history.data) setEntries((current) => mergeHistory(current, history.data ?? []));
  }, [history.data]);
  useEffect(() => {
    if (isUnauthorized(history.error)) onExpired?.();
  }, [history.error, onExpired]);
  useEffect(() => {
    if (!retryAt) return;
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, [retryAt]);

  const threads = threadsOf(entries);
  const thread = fresh ? [] : (threads.at(-1) ?? []);
  const last = thread.at(-1)?.attempt ?? null;
  const full = thread.length >= MAX_THREAD;
  const unresolved = entries.find((entry) => entry.attempt === null);
  const running = entries.some((entry) => active(entry.attempt));
  const cooldown = Math.max(0, Math.ceil((retryAt - now) / 1000));

  async function send(entry: ConversationEntry) {
    if (submitting.current || cooldown > 0) return;
    submitting.current = true;
    setPending(true);
    setError(null);
    try {
      const attempt = await requestJson<Attempt>("/api/attempts", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` },
        body: JSON.stringify({
          messages: entry.messages,
          idempotency_key: entry.key,
          continues: entry.continues ?? null,
        }),
      });
      if (!mounted.current) return;
      setEntries((current) =>
        current.map((item) => (item.key === entry.key ? { ...item, attempt } : item)),
      );
      setRetryAt(0);
      history.refresh();
    } catch (cause) {
      if (!mounted.current) return;
      if (isUnauthorized(cause)) {
        onExpired?.();
        return;
      }
      // A transport error may happen after acceptance. Keep the exact payload/key until
      // reconciliation or retry. A definite rejection can be edited safely.
      const status = cause instanceof ApiError ? cause.status : null;
      // Una conversación que ya no se puede continuar (404/409) se retoma en una nueva.
      const stale = Boolean(entry.continues) && (status === 404 || status === 409);
      if (status === 422 || stale) {
        setEntries((current) => current.filter((item) => item.key !== entry.key));
        setRestored(entry.messages.join("\n"));
        if (stale) setFresh(true);
      }
      if (cause instanceof ApiError && status === 429) {
        const delay = cause.retryAfterMs ?? 5000;
        setNow(Date.now());
        setRetryAt(Date.now() + delay);
      }
      setError(errorMessage(cause));
      history.refresh();
    } finally {
      submitting.current = false;
      if (mounted.current) setPending(false);
    }
  }

  function submit(text: string): boolean {
    if (submitting.current || running || pending || !history.data || !text.trim()) return false;
    const entry: ConversationEntry = {
      key: newKey(),
      messages: [text.trim()],
      attempt: null,
      continues: last && !active(last) && !full ? last.id : null,
    };
    const next = [...entries, entry];
    saveHistory(session.id, next);
    setEntries(next);
    setFresh(false);
    setRestored(null);
    void send(entry);
    return true;
  }

  return {
    entries,
    threads,
    full,
    fresh,
    startFresh: () => setFresh(true),
    pending,
    running,
    unresolved,
    cooldown,
    error,
    restored,
    history,
    submit,
    retry: (entry: ConversationEntry) => void send(entry),
  };
}
