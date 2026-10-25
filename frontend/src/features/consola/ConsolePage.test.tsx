import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ConsolePage } from "./ConsolePage";

vi.mock("../participant/AttemptChat", async () => {
  const { createElement } = await import("react");
  return {
    AttemptChat: ({ session }: { session: { id: string } }) =>
      createElement("p", null, `chat:${session.id}`),
  };
});

const PARTICIPANT_KEY = "agent-zero:participant:v1";
const PAST_KEY = "agent-zero:consola:past:v1";

function sessionFor(n: number) {
  return {
    id: `sess-${n}`,
    token: `token-${n}`,
    alias: `Interno-consola-${n}`,
    created_at: "2026-10-25T10:00:00Z",
    expires_at: "2099-10-25T11:00:00Z",
    customer_name: "Ana",
    order_ids: ["B-2001"],
    objectives: [],
  };
}

function mockConsole() {
  let created = 0;
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path === "/api/sessions") {
      created += 1;
      return Response.json(sessionFor(created));
    }
    if (path.startsWith("/api/operator/audit/chats/")) {
      return Response.json({ detail: "Chat no encontrado." }, { status: 404 });
    }
    throw new Error(`Unexpected request: ${path}`);
  });
}

async function login() {
  await userEvent.type(screen.getByLabelText("Secreto de operador"), "operator-secret-123");
  await userEvent.click(screen.getByRole("button", { name: "Acceder" }));
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("consola de pruebas", () => {
  it("abre una sesión interna y muestra su chat", async () => {
    const fetch = mockConsole();
    render(<ConsolePage />);
    await login();
    expect(await screen.findByText("chat:sess-1")).toBeInTheDocument();

    const [path, init] = fetch.mock.calls[0] ?? [];
    expect(path).toBe("/api/sessions");
    expect(init?.headers).toEqual(
      expect.objectContaining({ "X-Operator-Secret": "operator-secret-123" }),
    );
    expect(JSON.parse(String(init?.body)).alias.startsWith("Interno-consola")).toBe(true);
    expect(localStorage.getItem(PARTICIPANT_KEY)).toBeNull();
  });

  it("Nueva sesión reinicia el chat y archiva la sesión anterior", async () => {
    const fetch = mockConsole();
    render(<ConsolePage />);
    await login();
    await screen.findByText("chat:sess-1");

    await userEvent.click(screen.getByRole("button", { name: "Nueva sesión" }));
    expect(await screen.findByText("chat:sess-2")).toBeInTheDocument();
    expect(fetch.mock.calls.filter(([path]) => path === "/api/sessions")).toHaveLength(2);

    const past = JSON.parse(localStorage.getItem(PAST_KEY) ?? "[]") as { id: string }[];
    expect(past.map((item) => item.id)).toEqual(["sess-1"]);
    expect(localStorage.getItem(PARTICIPANT_KEY)).toBeNull();
  });
});
