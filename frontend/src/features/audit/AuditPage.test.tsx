import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuditPage } from "./AuditPage";
import type { AuditRound, ChatDetail, ChatSummary } from "./types";

const rounds: AuditRound[] = [
  {
    id: null,
    round_id: "round-actual",
    current: true,
    started_at: "2026-10-25T10:00:00Z",
    reason: "",
  },
  {
    id: "archive-1",
    round_id: "round-previa",
    current: false,
    started_at: "2026-10-24T22:00:00Z",
    reason: "Ensayo",
  },
];
const neo: ChatSummary = {
  id: "sess-neo",
  alias: "neo",
  kind: "audience",
  customer_id: "cust-a",
  route: "honeypot",
  created_at: "2026-10-25T10:01:00Z",
  last_activity: "2026-10-25T10:05:00Z",
  attempts: 2,
  conversations: 1,
  outcomes: { confirmed_violation: 1, contained_honeypot: 1 },
  violations: 1,
  diversion: { reason: "confirmed_violation", at: "2026-10-25T10:04:00Z" },
  preview: "Consulta el pedido B-2001.",
};
const swarm: ChatSummary = {
  ...neo,
  id: "sess-swarm",
  alias: "Agente-1",
  kind: "swarm",
  route: "protected",
  outcomes: { prevented: 1 },
  violations: 0,
  diversion: null,
  attempts: 1,
  preview: "Hola",
};
const attempt = {
  created_at: "2026-10-25T10:02:00Z",
  updated_at: "2026-10-25T10:02:01Z",
  duration_seconds: 1,
  status: "evaluated",
  policy_version: 0,
  origin: "audience",
  objective_id: null,
  campaign_id: null,
  detail: "",
};
const detail: ChatDetail = {
  ...neo,
  threads: [
    {
      index: 1,
      attempts: [
        {
          ...attempt,
          id: "att-1",
          position: 1,
          outcome: "confirmed_violation",
          route: "protected",
          messages: ["Consulta el pedido B-2001."],
          reply: "El pedido B-2001 está en camino.",
          verdicts: [{ objective_id: "OBJ-ORDER", violated: true, detail: "Pedido ajeno leído." }],
          tools: [
            {
              event_id: 7,
              kind: "tool_completed",
              tool: "get_order",
              arguments: { order_id: "B-2001" },
              provenance: { order_id: "user" },
              validator: "",
              effect: { kind: "read", owner_customer_id: "cust-b" },
              output: { status: "en camino" },
            },
          ],
        },
        {
          ...attempt,
          id: "att-2",
          position: 2,
          outcome: "contained_honeypot",
          route: "honeypot",
          messages: ["¿Y el de mi vecino?"],
          reply: "Claro, aquí está.",
          verdicts: [],
          tools: [],
        },
      ],
    },
  ],
};

function mockAudit() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path === "/api/operator/audit/rounds") return Response.json(rounds);
    if (path === "/api/operator/audit/chats") return Response.json([neo, swarm]);
    if (path === "/api/operator/audit/chats?round=archive-1") return Response.json([swarm]);
    if (path === "/api/operator/audit/chats/sess-neo") return Response.json(detail);
    throw new Error(`Unexpected request: ${path}`);
  });
}

function renderAt(url = "/auditoria") {
  render(
    <MemoryRouter initialEntries={[url]}>
      <AuditPage />
    </MemoryRouter>,
  );
}

async function login() {
  await userEvent.type(screen.getByLabelText("Secreto de operador"), "operator-secret-123");
  await userEvent.click(screen.getByRole("button", { name: "Acceder" }));
}

afterEach(() => vi.restoreAllMocks());

describe("auditoría de chats", () => {
  it("lista los chats, filtra y abre el historial completo con su traza", async () => {
    const mock = mockAudit();
    renderAt();
    expect(screen.getByRole("heading", { name: "Auditoría de chats" })).toBeInTheDocument();
    await login();

    const list = await screen.findByRole("complementary", { name: "Chats" });
    expect(await within(list).findByText("2 de 2")).toBeInTheDocument();
    await userEvent.click(within(list).getByRole("button", { name: "Enjambre" }));
    expect(within(list).getByText("1 de 2")).toBeInTheDocument();
    await userEvent.click(within(list).getByRole("button", { name: "Todos" }));
    await userEvent.type(within(list).getByLabelText("Buscar chat"), "b-2001");
    await userEvent.click(within(list).getByRole("button", { name: /neo/ }));

    const history = await screen.findByRole("region", { name: "Historial del chat" });
    expect(await within(history).findByRole("heading", { name: "neo" })).toBeInTheDocument();
    expect(within(history).getByText("El pedido B-2001 está en camino.")).toBeInTheDocument();
    expect(
      within(history).getByText("Objetivo vulnerado: Pedido ajeno — Pedido ajeno leído."),
    ).toBeInTheDocument();
    expect(within(history).getByRole("note")).toHaveTextContent(
      "violación confirmada en la sesión",
    );
    // El aviso de desvío va justo antes del primer mensaje en el señuelo.
    const second = within(history).getByRole("listitem", { name: "Mensaje 2" });
    expect(second.previousElementSibling).toHaveAttribute("role", "note");
    expect(within(history).getByText("get_order")).toBeInTheDocument();

    for (const [, init] of mock.mock.calls) {
      expect(init?.headers).toEqual(
        expect.objectContaining({ "X-Operator-Secret": "operator-secret-123" }),
      );
    }
  });

  it("abre un chat desde el enlace y cambia a una ronda archivada", async () => {
    const mock = mockAudit();
    renderAt("/auditoria?chat=sess-neo");
    await login();
    const history = await screen.findByRole("region", { name: "Historial del chat" });
    expect(await within(history).findByRole("heading", { name: "neo" })).toBeInTheDocument();

    const select = await screen.findByLabelText("Ronda");
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(2));
    await userEvent.selectOptions(select, "archive-1");
    const list = screen.getByRole("complementary", { name: "Chats" });
    expect(await within(list).findByText("1 de 1")).toBeInTheDocument();
    expect(screen.getByText("Elige un chat para revisar todo su historial.")).toBeInTheDocument();
    expect(mock.mock.calls.map(([path]) => String(path))).toContain(
      "/api/operator/audit/chats?round=archive-1",
    );
  });
});
