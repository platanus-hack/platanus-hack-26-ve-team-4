import { ApiError, errorMessage, requestJson } from "../../shared/api/http";
import { createTestSession, testAlias } from "../operator/testSession";
import type { Attempt } from "../participant/types";
import type { DemoCase } from "./catalog";
import { fill, placeholders } from "./fill";

export type ChatPhase = "creating" | "typing" | "waiting" | "done" | "error";

export interface ChatTurn {
  message: string;
  attempt: Attempt | null;
}

export interface ChatRun {
  key: string;
  caseId: string;
  alias: string;
  sessionId: string | null;
  phase: ChatPhase;
  turns: ChatTurn[];
  error: string | null;
}

export interface Timing {
  typingMs: number;
  pollMs: number;
  attemptTimeoutMs: number;
  retries: number;
}

export const TIMING: Timing = {
  typingMs: 1200,
  pollMs: 1000,
  attemptTimeoutMs: 90_000,
  retries: 5,
};

const TERMINAL = new Set(["evaluated", "inconclusive"]);

export function chatAlias(item: DemoCase, copy: number): string {
  const name = item.persona.split(" ")[0] ?? "";
  return testAlias(`${item.id} ${name} ${copy}`, item.id);
}

function pause(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(signal.reason);
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(signal.reason);
      },
      { once: true },
    );
  });
}

function key(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(12)), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

async function submit(
  token: string,
  message: string,
  continues: string | null,
  signal: AbortSignal,
  timing: Timing,
): Promise<Attempt> {
  const idempotency = key();
  for (let tries = 0; ; tries += 1) {
    try {
      return await requestJson<Attempt>("/api/attempts", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ messages: [message], idempotency_key: idempotency, continues }),
        signal,
      });
    } catch (cause) {
      if (!(cause instanceof ApiError) || cause.status !== 429 || tries >= timing.retries)
        throw cause;
      await pause(cause.retryAfterMs ?? 3000, signal);
    }
  }
}

async function settle(
  token: string,
  attempt: Attempt,
  signal: AbortSignal,
  timing: Timing,
  onProgress: (attempt: Attempt) => void,
): Promise<Attempt> {
  const deadline = Date.now() + timing.attemptTimeoutMs;
  let current = attempt;
  while (!TERMINAL.has(current.status)) {
    if (Date.now() > deadline) throw new Error("La respuesta tardó demasiado.");
    await pause(timing.pollMs, signal);
    current = await requestJson<Attempt>(`/api/attempts/${encodeURIComponent(attempt.id)}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal,
    });
    onProgress(current);
  }
  return current;
}

export async function runChat(
  secret: string,
  item: DemoCase,
  run: ChatRun,
  update: (run: ChatRun) => void,
  signal: AbortSignal,
  timing: Timing = TIMING,
): Promise<void> {
  let state = run;
  const set = (patch: Partial<ChatRun>) => {
    state = { ...state, ...patch };
    update(state);
  };
  try {
    const session = await createTestSession(secret, run.alias);
    set({ sessionId: session.id });
    const values = placeholders(session.order_ids);
    let previous: string | null = null;
    for (const template of item.turns) {
      const message = fill(template, values);
      set({ phase: "typing" });
      await pause(timing.typingMs, signal);
      const turns = [...state.turns, { message, attempt: null }];
      set({ phase: "waiting", turns });
      const replace = (attempt: Attempt) =>
        set({
          turns: state.turns.map((turn, i) =>
            i === turns.length - 1 ? { message, attempt } : turn,
          ),
        });
      const sent = await submit(session.token, message, previous, signal, timing);
      replace(sent);
      const finished = await settle(session.token, sent, signal, timing, replace);
      replace(finished);
      previous = finished.id;
    }
    set({ phase: "done" });
  } catch (cause) {
    if (signal.aborted) return;
    set({ phase: "error", error: errorMessage(cause) });
  }
}
