import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TraceEvent } from "../types";
import { useArenaEvents } from "./useArenaEvents";

class FakeEventSource {
  static last: FakeEventSource | null = null;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  private listeners = new Map<string, (message: MessageEvent<string>) => void>();

  readonly url: string;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.last = this;
  }

  addEventListener(type: string, listener: (message: MessageEvent<string>) => void) {
    this.listeners.set(type, listener);
  }

  emit(event: TraceEvent) {
    const message = new MessageEvent(event.type, { data: JSON.stringify(event) });
    this.listeners.get(event.type)?.(message);
  }

  close() {
    this.closed = true;
  }
}

function traceEvent(id: number): TraceEvent {
  return {
    id,
    type: "attempt_queued",
    visibility: "public",
    attempt_id: null,
    session_id: null,
    policy_version: null,
    timestamp: "2026-10-24T00:00:00Z",
    data: {},
  };
}

describe("useArenaEvents", () => {
  beforeEach(() => {
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("acumula eventos nuevos primero y descarta duplicados por id", () => {
    const { result } = renderHook(() => useArenaEvents());
    const source = FakeEventSource.last as FakeEventSource;

    act(() => {
      source.onopen?.();
      source.emit(traceEvent(1));
      source.emit(traceEvent(2));
      source.emit(traceEvent(2));
    });

    expect(result.current.connection).toBe("open");
    expect(result.current.events.map((event) => event.id)).toEqual([2, 1]);
  });

  it("cierra la conexión al desmontar", () => {
    const { unmount } = renderHook(() => useArenaEvents());
    const source = FakeEventSource.last as FakeEventSource;

    unmount();

    expect(source.closed).toBe(true);
  });
});
