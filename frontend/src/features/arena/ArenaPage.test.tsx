import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, type MockInstance, vi } from "vitest";
import { ArenaPage } from "./ArenaPage";
import type { ArenaState, TraceEvent } from "./types";

class FakeEventSource {
  static last: FakeEventSource | null = null;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
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
    this.listeners.get(event.type)?.(new MessageEvent(event.type, { data: JSON.stringify(event) }));
  }

  close() {}
}

const STATE: ArenaState = {
  accepting: true,
  policy_version: 1,
  attempts_total: 6,
  queued: 1,
  running: 1,
  finished: 4,
  apparent_successes: 2,
  prevented: 1,
  not_achieved: 1,
  inconclusive: 0,
  findings_open: null,
};

function publicEvent(id: number, type: TraceEvent["type"], data: TraceEvent["data"]): TraceEvent {
  return {
    id,
    type,
    visibility: "public",
    attempt_id: null,
    session_id: null,
    policy_version: 1,
    timestamp: "2026-10-24T06:51:12Z",
    data,
  };
}

let fetchMock: MockInstance<typeof fetch>;

beforeEach(() => {
  vi.stubGlobal("EventSource", FakeEventSource);
  fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json(STATE));
});

afterEach(() => vi.unstubAllGlobals());

describe("ArenaPage", () => {
  it("muestra los cinco indicadores con texto y sin inventar hallazgos", async () => {
    render(<ArenaPage />);

    expect(await screen.findByText("4/6")).toBeInTheDocument();
    expect(screen.getByText("Éxitos aparentes · provisional").nextSibling).toHaveTextContent("2");
    expect(screen.getByText("Intentos detenidos").nextSibling).toHaveTextContent("1");
    expect(screen.getByText("Hallazgos abiertos").nextSibling).toHaveTextContent("Sin datos");
    expect(screen.getByText("Versión activa").nextSibling).toHaveTextContent("v1");
  });

  it("el QR lleva a la ruta de participantes y no a operación", () => {
    render(<ArenaPage />);

    const qr = screen.getByRole("img", { name: /Código QR hacia/ });
    expect(qr.querySelector("svg")).not.toBeNull();
    expect(qr).toHaveAccessibleName(`Código QR hacia ${window.location.host}/`);
    expect(screen.getByText(`${window.location.host}/`)).toBeInTheDocument();
  });

  it("solo consulta datos públicos", async () => {
    render(<ArenaPage />);
    await screen.findByText("4/6");

    expect(FakeEventSource.last?.url).toBe("/api/arena/events");
    const urls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(urls.every((url) => url === "/api/arena/state")).toBe(true);
  });

  it("muestra la actividad pública y refresca los indicadores con cada evento", async () => {
    render(<ArenaPage />);
    await screen.findByText("4/6");
    const before = fetchMock.mock.calls.length;

    act(() => {
      FakeEventSource.last?.onopen?.();
      FakeEventSource.last?.emit(
        publicEvent(7, "attempt_evaluated", { status: "evaluated", outcome: "apparent_success" }),
      );
    });

    expect(screen.getByRole("status", { name: "" })).toHaveTextContent("En vivo");
    expect(screen.getByText("Intento terminado")).toBeInTheDocument();
    expect(screen.getByText("Éxito aparente · pendiente de verificación")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(before));
  });
});
