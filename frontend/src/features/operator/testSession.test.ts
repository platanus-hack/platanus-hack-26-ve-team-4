import { afterEach, describe, expect, it, vi } from "vitest";
import { session } from "../../test/fixtures";
import { loadSession } from "../participant/storage";
import { createTestSession, openTestChat, testAlias } from "./testSession";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("testAlias", () => {
  it("usa el prefijo reservado con el nombre o el sufijo", () => {
    expect(testAlias(" Fer  M ", "abc12")).toBe("Interno-Fer-M");
    expect(testAlias("", "abc12")).toBe("Interno-abc12");
  });

  it("no pasa de 40 caracteres", () => {
    expect(testAlias("x".repeat(60), "s")).toHaveLength(40);
  });
});

describe("createTestSession", () => {
  it("manda el secreto de operador al crear la sesión", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(session));
    await createTestSession("secreto", "Interno-a");
    const [path, init] = fetch.mock.calls[0] ?? [];
    expect(path).toBe("/api/sessions");
    expect(new Headers(init?.headers).get("X-Operator-Secret")).toBe("secreto");
    expect(JSON.parse(String(init?.body))).toEqual({ alias: "Interno-a", accepted_rules: true });
  });
});

describe("openTestChat", () => {
  it("guarda la sesión y abre el chat en otra pestaña", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(session));
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    await openTestChat("secreto", "Interno-a");
    expect(loadSession()?.id).toBe(session.id);
    expect(open).toHaveBeenCalledWith("/", "_blank", "noopener");
  });
});
