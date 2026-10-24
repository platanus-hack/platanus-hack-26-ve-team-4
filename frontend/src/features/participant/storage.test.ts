import { describe, expect, it, vi } from "vitest";
import { session } from "../../test/fixtures";
import { loadHistory, loadSession, saveHistory, saveSession } from "./storage";

describe("recuperación del navegador", () => {
  it("tolera JSON corrupto y metadatos incompletos sin aceptar otra identidad", () => {
    sessionStorage.setItem("agent-zero:participant:v1", "{");
    expect(loadSession()).toBeNull();
    sessionStorage.setItem("agent-zero:participant:v1", JSON.stringify({ id: "fake", token: "x" }));
    expect(loadSession()).toBeNull();
    sessionStorage.setItem(
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
  it("conserva credenciales solo en esta pestaña y permite invalidarlas", () => {
    saveSession(session);
    expect(loadSession()).toEqual(session);
    expect(localStorage.length).toBe(0);
    saveSession(null);
    expect(loadSession()).toBeNull();
  });
  it("no convierte falta de almacenamiento en una mutación fallida", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("quota", "QuotaExceededError");
    });
    expect(() => saveSession(session)).not.toThrow();
    expect(() => saveHistory(session.id, [])).not.toThrow();
  });
});
