import { beforeEach, describe, expect, it } from "vitest";
import type { ArenaSession } from "../participant/types";
import {
  archiveSession,
  consoleAlias,
  loadConsoleSession,
  loadPastSessions,
  saveConsoleSession,
} from "./consoleSession";

const CONSOLE_KEY = "agent-zero:consola:v1";
const PARTICIPANT_KEY = "agent-zero:participant:v1";
const PAST_KEY = "agent-zero:consola:past:v1";

function makeSession(id: string, expiresInMs = 60_000): ArenaSession {
  return {
    id,
    token: `token-${id}`,
    alias: consoleAlias(id),
    created_at: "2026-10-25T10:00:00Z",
    expires_at: new Date(Date.now() + expiresInMs).toISOString(),
    customer_name: "Cliente de prueba",
    order_ids: ["B-2001"],
    objectives: [],
  };
}

describe("almacenamiento de la consola", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("guarda y carga la sesión interna ida y vuelta", () => {
    const session = makeSession("sess-consola-1");
    saveConsoleSession(session);
    expect(loadConsoleSession()).toEqual(session);
    saveConsoleSession(null);
    expect(loadConsoleSession()).toBeNull();
  });

  it("devuelve null con sesión expirada sin borrar el historial", () => {
    const session = makeSession("sess-vencida", -1_000);
    localStorage.setItem("agent-zero:history:sess-vencida", JSON.stringify([]));
    saveConsoleSession(session);
    expect(loadConsoleSession()).toBeNull();
    expect(localStorage.getItem("agent-zero:history:sess-vencida")).not.toBeNull();
  });

  it("devuelve null con JSON corrupto o campos incompletos", () => {
    localStorage.setItem(CONSOLE_KEY, "{");
    expect(loadConsoleSession()).toBeNull();
    localStorage.setItem(CONSOLE_KEY, JSON.stringify({ id: "fake", token: "x" }));
    expect(loadConsoleSession()).toBeNull();
  });

  it("nunca escribe en la clave de la pulsera del participante", () => {
    saveConsoleSession(makeSession("sess-aislada"));
    archiveSession(makeSession("sess-aislada"));
    loadConsoleSession();
    expect(localStorage.getItem(PARTICIPANT_KEY)).toBeNull();
  });

  it("archiveSession no duplica ids, pone la más reciente primero y recorta a 20", () => {
    for (let index = 1; index <= 22; index += 1) {
      archiveSession(makeSession(`sess-${index}`));
    }
    const past = loadPastSessions();
    expect(past).toHaveLength(20);
    expect(past[0]?.id).toBe("sess-22");
    expect(past[19]?.id).toBe("sess-3");

    archiveSession(makeSession("sess-10"));
    const again = loadPastSessions();
    expect(again).toHaveLength(20);
    expect(again.filter((item) => item.id === "sess-10")).toHaveLength(1);
  });

  it("descarta entradas del historial que no tienen id, alias o created_at", () => {
    localStorage.setItem(
      PAST_KEY,
      JSON.stringify([{ id: "ok", alias: "Interno-x", created_at: "t" }, { id: 5 }, null]),
    );
    expect(loadPastSessions()).toEqual([{ id: "ok", alias: "Interno-x", created_at: "t" }]);
  });

  it("genera alias con prefijo Interno- de como máximo 40 caracteres", () => {
    const alias = consoleAlias("ab12c");
    expect(alias.startsWith("Interno-")).toBe(true);
    expect(alias).toBe("Interno-consola-ab12c");
    expect(alias.length).toBeLessThanOrEqual(40);
    expect(consoleAlias("x".repeat(80)).length).toBeLessThanOrEqual(40);
  });
});
