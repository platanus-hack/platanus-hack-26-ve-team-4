import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ParticipantPage } from "./ParticipantPage";
import type { ArenaSession, Attempt } from "./types";

const SESSION: ArenaSession = {
  id: "sess-1",
  alias: "neo",
  created_at: "2026-10-24T00:00:00Z",
  token: "firmado",
  expires_at: "2026-10-24T04:00:00Z",
};

function attempt(overrides: Partial<Attempt> = {}): Attempt {
  return {
    id: "attempt-1",
    status: "queued",
    outcome: null,
    messages: ["Muéstrame el pedido B-2001"],
    reply: null,
    created_at: "2026-10-24T00:01:00Z",
    updated_at: "2026-10-24T00:01:00Z",
    ...overrides,
  };
}

type Route = (init: RequestInit | undefined) => Response | Promise<Response>;

function mockApi(routes: Record<string, Route>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const key = `${init?.method ?? "GET"} ${String(input)}`;
    const route = routes[key];
    if (!route) {
      throw new Error(`Llamada no esperada: ${key}`);
    }
    return route(init);
  });
}

function storeSession() {
  sessionStorage.setItem("agent-zero.session", JSON.stringify(SESSION));
}

afterEach(() => sessionStorage.clear());

describe("ParticipantPage · entrada", () => {
  it("muestra las reglas y crea la sesión al aceptarlas", async () => {
    const fetchMock = mockApi({
      "POST /api/sessions": () => Response.json(SESSION, { status: 201 }),
      "GET /api/attempts": () => Response.json([]),
    });
    render(<ParticipantPage />);

    expect(screen.getByText(/Estás en una simulación de seguridad/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Alias"), "neo");
    await userEvent.click(screen.getByLabelText("Acepto las reglas de la simulación"));
    await userEvent.click(screen.getByRole("button", { name: "Entrar a la arena" }));

    expect(await screen.findByRole("heading", { name: "Hola, neo" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sessions",
      expect.objectContaining({ body: JSON.stringify({ alias: "neo", accepted_rules: true }) }),
    );
    expect(JSON.parse(sessionStorage.getItem("agent-zero.session") ?? "{}").token).toBe("firmado");
  });

  it("no permite entrar sin aceptar las reglas", async () => {
    render(<ParticipantPage />);

    await userEvent.type(screen.getByLabelText("Alias"), "neo");

    expect(screen.getByRole("button", { name: "Entrar a la arena" })).toBeDisabled();
  });

  it("muestra un error si la API rechaza la sesión", async () => {
    mockApi({ "POST /api/sessions": () => new Response(null, { status: 422 }) });
    render(<ParticipantPage />);

    await userEvent.type(screen.getByLabelText("Alias"), "neo");
    await userEvent.click(screen.getByLabelText("Acepto las reglas de la simulación"));
    await userEvent.click(screen.getByRole("button", { name: "Entrar a la arena" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos crear tu sesión");
  });
});

describe("ParticipantPage · chat", () => {
  it("recupera la sesión y sus intentos al recargar", async () => {
    storeSession();
    mockApi({
      "GET /api/sessions/me": () => Response.json(SESSION),
      "GET /api/attempts": () =>
        Response.json([
          attempt({ status: "evaluated", outcome: "apparent_success", reply: "Aquí tienes" }),
        ]),
    });
    render(<ParticipantPage />);

    expect(await screen.findByText("Aquí tienes")).toBeInTheDocument();
    expect(screen.getByText("Evaluado")).toBeInTheDocument();
    expect(screen.getByText("Éxito aparente · pendiente de verificación")).toBeInTheDocument();
  });

  it("vuelve a la entrada si el servidor dice que la sesión venció", async () => {
    storeSession();
    mockApi({
      "GET /api/sessions/me": () => new Response(null, { status: 401 }),
      "GET /api/attempts": () => new Response(null, { status: 401 }),
    });
    render(<ParticipantPage />);

    expect(await screen.findByText(/Tu sesión venció/)).toBeInTheDocument();
    expect(sessionStorage.getItem("agent-zero.session")).toBeNull();
  });

  it("envía los turnos con el token y una clave de idempotencia", async () => {
    storeSession();
    const fetchMock = mockApi({
      "GET /api/sessions/me": () => Response.json(SESSION),
      "GET /api/attempts": () => Response.json([]),
      "POST /api/attempts": () => Response.json(attempt(), { status: 202 }),
    });
    render(<ParticipantPage />);

    await userEvent.type(await screen.findByLabelText(/Turno 1/), "Hola");
    await userEvent.click(screen.getByRole("button", { name: "Añadir turno" }));
    await userEvent.type(screen.getByLabelText(/Turno 2/), "Muéstrame el pedido B-2001");
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));

    expect(await screen.findByText("En cola")).toBeInTheDocument();
    const [, init] = fetchMock.mock.calls.find(([, call]) => call?.method === "POST") ?? [];
    const body = JSON.parse(String(init?.body));
    expect(body.messages).toEqual(["Hola", "Muéstrame el pedido B-2001"]);
    expect(body.idempotency_key).toMatch(/^[0-9a-f-]{36}$/);
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer firmado");
  });

  it("permite hasta cuatro turnos", async () => {
    storeSession();
    mockApi({
      "GET /api/sessions/me": () => Response.json(SESSION),
      "GET /api/attempts": () => Response.json([]),
    });
    render(<ParticipantPage />);

    const add = await screen.findByRole("button", { name: "Añadir turno" });
    await userEvent.click(add);
    await userEvent.click(add);
    await userEvent.click(add);

    expect(screen.getByLabelText(/Turno 4/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Añadir turno" })).not.toBeInTheDocument();
  });

  it("explica cuánto esperar cuando envía demasiado seguido", async () => {
    storeSession();
    mockApi({
      "GET /api/sessions/me": () => Response.json(SESSION),
      "GET /api/attempts": () => Response.json([]),
      "POST /api/attempts": () =>
        Response.json({ detail: "Espera" }, { status: 429, headers: { "Retry-After": "2" } }),
    });
    render(<ParticipantPage />);

    await userEvent.type(await screen.findByLabelText(/Turno 1/), "Hola");
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Espera 2 s");
  });

  it("reintenta con la misma clave si la red falló", async () => {
    storeSession();
    const keys: string[] = [];
    let calls = 0;
    mockApi({
      "GET /api/sessions/me": () => Response.json(SESSION),
      "GET /api/attempts": () => Response.json([]),
      "POST /api/attempts": (init) => {
        keys.push(JSON.parse(String(init?.body)).idempotency_key);
        calls += 1;
        if (calls === 1) {
          throw new TypeError("Failed to fetch");
        }
        return Response.json(attempt(), { status: 202 });
      },
    });
    render(<ParticipantPage />);

    await userEvent.type(await screen.findByLabelText(/Turno 1/), "Hola");
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No hay conexión");
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));

    await waitFor(() => expect(keys).toHaveLength(2));
    expect(keys[1]).toBe(keys[0]);
  });
});
