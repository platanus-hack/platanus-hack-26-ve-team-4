import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { deferred } from "../../test/fixtures";
import { usePolling } from "./usePolling";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("polling durable", () => {
  it("no solapa solicitudes lentas y programa desde su finalización", async () => {
    const response = deferred<number>();
    const load = vi.fn(() => response.promise);
    const { result } = renderHook(() => usePolling(load, 1000));
    await act(async () => vi.advanceTimersByTimeAsync(10_000));
    expect(load).toHaveBeenCalledOnce();
    await act(async () => response.resolve(42));
    expect(result.current.data).toBe(42);
    await act(async () => vi.advanceTimersByTimeAsync(999));
    expect(load).toHaveBeenCalledOnce();
    await act(async () => vi.advanceTimersByTimeAsync(1));
    expect(load).toHaveBeenCalledTimes(2);
  });
  it("conserva último dato, informa caída y limpia error al reconectar", async () => {
    const load = vi
      .fn()
      .mockResolvedValueOnce(1)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue(2);
    const { result } = renderHook(() => usePolling<number>(load, 1000));
    await act(async () => {});
    expect(result.current.data).toBe(1);
    await act(async () => vi.advanceTimersByTimeAsync(1000));
    expect(result.current.data).toBe(1);
    expect(result.current.error).toBeInstanceOf(Error);
    await act(async () => vi.advanceTimersByTimeAsync(1000));
    expect(result.current.data).toBe(2);
    expect(result.current.error).toBeNull();
  });
  it("ignora respuestas tardías de credenciales anteriores aunque fetch no aborte", async () => {
    const old = deferred<string>();
    const first = vi.fn((_signal: AbortSignal) => old.promise);
    const second = vi.fn(async () => "nuevo");
    const { result, rerender } = renderHook(({ load }) => usePolling(load), {
      initialProps: { load: first as (signal: AbortSignal) => Promise<string> },
    });
    const signal = first.mock.calls[0]?.[0];
    rerender({ load: second });
    await act(async () => {});
    await act(async () => old.resolve("privado anterior"));
    expect(result.current.data).toBe("nuevo");
    expect(signal?.aborted).toBe(true);
  });
  it("refresh invalida la solicitud anterior y unmount cierra todo", async () => {
    const load = vi.fn(async (_signal: AbortSignal) => 1);
    const { result, unmount } = renderHook(() => usePolling(load));
    await act(async () => {});
    act(() => result.current.refresh());
    await act(async () => {});
    expect(load).toHaveBeenCalledTimes(2);
    expect(load.mock.calls[0]?.[0].aborted).toBe(true);
    const lastSignal = load.mock.calls[1]?.[0];
    unmount();
    expect(lastSignal?.aborted).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
  });
});
