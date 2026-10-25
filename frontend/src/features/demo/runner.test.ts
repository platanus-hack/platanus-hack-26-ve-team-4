import { afterEach, describe, expect, it, vi } from "vitest";
import { session } from "../../test/fixtures";
import { caseById } from "./catalog";
import { type ChatRun, chatAlias, runChat } from "./runner";

const FAST = { typingMs: 0, pollMs: 0, attemptTimeoutMs: 5000, retries: 2 };

afterEach(() => vi.restoreAllMocks());

function start(caseId: string): ChatRun {
  return {
    key: "k",
    caseId,
    alias: chatAlias(caseById(caseId), 7),
    sessionId: null,
    phase: "creating",
    turns: [],
    error: null,
  };
}

describe("runChat", () => {
  it("abre una sesión interna y manda cada turno continuando el anterior", async () => {
    const bodies: Record<string, unknown>[] = [];
    let counter = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/api/sessions") return Response.json({ ...session, alias: "Interno-x" });
      if (init?.method === "POST") {
        bodies.push(JSON.parse(String(init.body)));
        counter += 1;
        return Response.json({ id: `att-${counter}`, status: "queued", reply: "" });
      }
      return Response.json({ id: url.split("/").at(-1), status: "evaluated", reply: "Listo." });
    });
    const updates: ChatRun[] = [];
    const item = caseById("N2-1");
    await runChat(
      "secreto",
      item,
      start("N2-1"),
      (run) => updates.push(run),
      new AbortController().signal,
      FAST,
    );
    const last = updates.at(-1);
    expect(last?.phase).toBe("done");
    expect(last?.turns.map((turn) => turn.attempt?.reply)).toEqual(["Listo.", "Listo."]);
    expect(bodies.map((body) => body.continues)).toEqual([null, "att-1"]);
    expect(String(bodies[1]?.messages)).toContain("A-1001");
  });

  it("reintenta tras un 429 y marca error si el servidor rechaza", async () => {
    let calls = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input) === "/api/sessions") return Response.json(session);
      calls += 1;
      return Response.json(
        { detail: "Demasiados intentos." },
        { status: 429, headers: { "Retry-After": "0" } },
      );
    });
    const updates: ChatRun[] = [];
    await runChat(
      "secreto",
      caseById("N0-1"),
      start("N0-1"),
      (run) => updates.push(run),
      new AbortController().signal,
      FAST,
    );
    expect(calls).toBe(3);
    expect(updates.at(-1)).toMatchObject({ phase: "error", error: "Demasiados intentos." });
  });

  it("usa el prefijo reservado de las pruebas internas", () => {
    expect(chatAlias(caseById("N4-2"), 7)).toBe("Interno-Auto-N4-2-Ingrid-7");
  });
});
