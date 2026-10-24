import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, errorMessage, requestJson } from "./http";

afterEach(() => vi.useRealTimers());

describe("HTTP transport", () => {
  it("propaga el detalle y Retry-After sin reintentar mutaciones", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        Response.json({ detail: "Cola llena" }, { status: 429, headers: { "Retry-After": "7" } }),
      );
    await expect(requestJson("/api/attempts", { method: "POST" })).rejects.toMatchObject({
      status: 429,
      message: "Cola llena",
      retryAfterMs: 7000,
    });
    expect(fetchMock).toHaveBeenCalledOnce();
  });
  it("interpreta Retry-After como fecha y tolera cuerpos no JSON", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-24T00:00:00Z"));
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("temporarily unavailable", {
        status: 503,
        headers: { "Retry-After": "Sat, 24 Oct 2026 00:00:12 GMT" },
      }),
    );
    await expect(requestJson("/api/arena/state")).rejects.toMatchObject({
      status: 503,
      retryAfterMs: 12_000,
      message: "La solicitud falló (503)",
    });
  });
  it("aborta una solicitud colgada al vencer el timeout", async () => {
    vi.useFakeTimers();
    vi.spyOn(globalThis, "fetch").mockImplementation(
      (_path, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(init.signal?.reason));
        }),
    );
    const promise = requestJson("/api/arena/state", undefined, 100);
    const check = expect(promise).rejects.toMatchObject({ name: "TimeoutError" });
    await vi.advanceTimersByTimeAsync(100);
    await check;
  });
  it("propaga cancelación del propietario y retira el temporizador", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(
      (_path, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => reject(init.signal?.reason));
        }),
    );
    const pending = requestJson("/api/attempts", { signal: controller.signal });
    const check = expect(pending).rejects.toMatchObject({ name: "AbortError" });
    controller.abort();
    await check;
    expect(fetchMock.mock.calls[0]?.[1]?.signal?.aborted).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });
  it("tolera respuestas sin contenido y evita caché de datos privados", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(null, { status: 204 }));
    await expect(requestJson("/api/operator/arena/pause")).resolves.toBeUndefined();
    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({
      cache: "no-store",
      credentials: "same-origin",
    });
  });
  it("no expone texto de errores internos de transporte al participante", () => {
    expect(errorMessage(new Error("provider_key=secret"))).not.toContain("secret");
    expect(errorMessage(new ApiError(409, "Ronda cerrada"))).toBe("Ronda cerrada");
  });
});
