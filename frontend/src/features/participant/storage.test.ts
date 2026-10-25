import { describe, expect, it, vi } from "vitest";
import { session } from "../../test/fixtures";
import {
  loadBatch,
  loadHistory,
  loadSession,
  saveBatch,
  saveHistory,
  saveSession,
} from "./storage";

const SESSION_KEY = "agent-zero:participant:v1";

describe("recuperación del navegador", () => {
  it("tolera JSON corrupto y metadatos incompletos sin aceptar otra identidad", () => {
    localStorage.setItem(SESSION_KEY, "{");
    expect(loadSession()).toBeNull();
    localStorage.setItem(SESSION_KEY, JSON.stringify({ id: "fake", token: "x" }));
    expect(loadSession()).toBeNull();
    localStorage.setItem(
      "agent-zero:history:sess-1",
      JSON.stringify([
        null,
        { key: "bad", messages: [] },
        { key: "ok", messages: ["Consulta propia"], attempt: null },
      ]),
    );
    expect(loadHistory("sess-1")).toEqual([
      { key: "ok", messages: ["Consulta propia"], attempt: null },
    ]);
  });
  it("conserva la pulsera al cerrar la pestaña para no crear otra sesión", () => {
    saveSession(session);
    // Una pestaña nueva no comparte sessionStorage, pero sí localStorage.
    sessionStorage.clear();
    expect(loadSession()).toEqual(session);
    expect(sessionStorage.length).toBe(0);
  });
  it("invalida la pulsera junto con su historial", () => {
    saveSession(session);
    saveHistory(session.id, [{ key: "k", messages: ["Hola"], attempt: null }]);
    saveSession(null);
    expect(loadSession()).toBeNull();
    expect(loadHistory(session.id)).toEqual([]);
  });
  it("descarta una pulsera vencida en vez de reutilizarla", () => {
    saveSession({ ...session, expires_at: "2020-01-01T00:00:00Z" });
    saveHistory(session.id, [{ key: "k", messages: ["Hola"], attempt: null }]);
    expect(loadSession()).toBeNull();
    expect(localStorage.getItem(SESSION_KEY)).toBeNull();
    expect(loadHistory(session.id)).toEqual([]);
  });
  it("migra la pulsera que una versión anterior dejó en sessionStorage", () => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    expect(loadSession()).toEqual(session);
    expect(sessionStorage.getItem(SESSION_KEY)).toBeNull();
    expect(localStorage.getItem(SESSION_KEY)).not.toBeNull();
  });
  it("no convierte falta de almacenamiento en una mutación fallida", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("quota", "QuotaExceededError");
    });
    expect(() => saveSession(session)).not.toThrow();
    expect(() => saveHistory(session.id, [])).not.toThrow();
  });
  it("guarda el lote sin enviar, descarta uno corrupto y lo borra al invalidar la pulsera", () => {
    saveSession(session);
    saveBatch(session.id, { texts: ["Hola", "otra"], first: 1, last: 2 });
    expect(loadBatch(session.id)).toEqual({ texts: ["Hola", "otra"], first: 1, last: 2 });
    localStorage.setItem(`agent-zero:batch:${session.id}`, JSON.stringify({ texts: [] }));
    expect(loadBatch(session.id)).toBeNull();
    saveBatch(session.id, { texts: ["Hola"], first: 1, last: 1 });
    saveSession(null);
    expect(loadBatch(session.id)).toBeNull();
  });
  it("conserva las partes de un lote enviado y descarta partes que no son texto", () => {
    saveHistory(session.id, [
      { key: "ok", messages: ["uno\ndos"], parts: ["uno", "dos"], attempt: null },
      { key: "bad", messages: ["x"], parts: [1 as unknown as string], attempt: null },
    ]);
    expect(loadHistory(session.id).map((entry) => entry.key)).toEqual(["ok"]);
  });
});
