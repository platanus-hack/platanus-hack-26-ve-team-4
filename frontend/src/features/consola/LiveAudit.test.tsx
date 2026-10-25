import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AuditAttempt, ChatDetail, ToolStep } from "../audit/types";
import { LiveAudit } from "./LiveAudit";

const denied: ToolStep = {
  event_id: 3,
  kind: "tool_denied",
  tool: "get_order",
  arguments: { order_id: "B-2001" },
  provenance: {},
  validator: "order_owner",
  effect: {},
  output: {},
  stage: "input",
  reason: "input_blocked",
};

function attempt(overrides: Partial<AuditAttempt>): AuditAttempt {
  return {
    id: "att-1",
    position: 1,
    created_at: "2026-10-25T10:02:00Z",
    updated_at: "2026-10-25T10:02:01Z",
    duration_seconds: 1,
    status: "evaluated",
    outcome: "prevented",
    route: "protected",
    policy_version: 0,
    origin: "test",
    objective_id: null,
    campaign_id: null,
    messages: ["Hola"],
    reply: "¡Hola!",
    verdicts: [],
    detail: "",
    tools: [],
    ...overrides,
  };
}

function detail(attempts: AuditAttempt[]): ChatDetail {
  return {
    id: "sess-1",
    alias: "Interno-consola-ab12c",
    kind: "test",
    customer_id: "cust-a",
    route: "protected",
    created_at: "2026-10-25T10:00:00Z",
    last_activity: "2026-10-25T10:05:00Z",
    attempts: attempts.length,
    conversations: 1,
    outcomes: {},
    violations: 0,
    diversion: null,
    preview: "",
    threads: [{ index: 1, attempts }],
    risk_score: 3,
    risk_signals: [{ validator: "order_owner", count: 2 }],
  };
}

const twoMessages = detail([
  attempt({ id: "att-1", position: 1, tools: [denied] }),
  attempt({
    id: "att-2",
    position: 2,
    status: "queued",
    outcome: null,
    messages: ["Consulta el pedido B-2001"],
    reply: "",
  }),
]);

function mockAudit(body: unknown, init?: ResponseInit) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async () => Response.json(body, init ?? { status: 200 }));
}

function renderLive(onUnauthorized = () => {}) {
  render(
    <LiveAudit secret="operator-secret-123" sessionId="sess-1" onUnauthorized={onUnauthorized} />,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("auditoría en vivo", () => {
  it("muestra el mensaje más reciente primero con su clasificación", async () => {
    mockAudit(twoMessages);
    renderLive();
    const cards = await screen.findAllByRole("listitem", { name: /Mensaje \d/ });
    expect(cards).toHaveLength(2);
    expect(cards[0]).toHaveAttribute("aria-label", "Mensaje 2");
    expect(cards[1]).toHaveAttribute("aria-label", "Mensaje 1");
    expect(within(cards[0] as HTMLElement).getByText("En cola")).toBeInTheDocument();
    expect(within(cards[1] as HTMLElement).getByText("Negado por order_owner")).toBeInTheDocument();
    expect(screen.getByText("Riesgo: 3")).toBeInTheDocument();
    expect(screen.getByText("Señales de riesgo: order_owner ×2")).toBeInTheDocument();
  });

  it("muestra la guía cuando la sesión aún no tiene mensajes", async () => {
    mockAudit(detail([]));
    renderLive();
    expect(
      await screen.findByText(
        "Escribe un mensaje en el chat: aquí verás cómo lo clasifica y qué hace el agente.",
      ),
    ).toBeInTheDocument();
  });

  it("trata un 404 como sesión sin mensajes y no como error", async () => {
    mockAudit({ detail: "Chat no encontrado." }, { status: 404 });
    renderLive();
    expect(await screen.findByText(/Escribe un mensaje en el chat/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("avisa de la respuesta 401 y pide volver al acceso", async () => {
    mockAudit({ detail: "Secreto inválido." }, { status: 401 });
    const onUnauthorized = vi.fn();
    renderLive(onUnauthorized);
    await vi.waitFor(() => expect(onUnauthorized).toHaveBeenCalled());
  });

  it("vuelve a consultar la auditoría a los 1500 ms", async () => {
    vi.useFakeTimers();
    const fetch = mockAudit(twoMessages);
    renderLive();
    await vi.advanceTimersByTimeAsync(0);
    expect(fetch).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1500);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(String(fetch.mock.calls[1]?.[0])).toBe("/api/operator/audit/chats/sess-1");
  });
});
