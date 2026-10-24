import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { arena, attempt, deferred, session } from "../../test/fixtures";
import { AttemptChat, mergeHistory } from "./AttemptChat";
import { loadHistory, saveHistory } from "./storage";
import type { Attempt } from "./types";

function mockApi(
  post: (init: RequestInit) => Promise<Response>,
  history: () => Promise<Response> = async () => Response.json([]),
  state = arena,
) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (path === "/api/arena/state") return Response.json(state);
    if (path === "/api/attempts" && init?.method === "POST") return post(init);
    if (path === "/api/attempts") return history();
    throw new Error(`Unexpected request ${path}`);
  });
}
async function enterMessage(text = "Consulta B-2001") {
  await userEvent.type(screen.getByLabelText("Mensaje al asistente"), text);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Enviar intento" })).not.toBeDisabled(),
  );
}

describe("AttemptChat", () => {
  it("envía con token y clave estable, conserva conversación y permite varios intentos", async () => {
    let number = 0;
    const fetchMock = mockApi(async () =>
      Response.json(attempt({ id: `attempt-${++number}` }), { status: 202 }),
    );
    render(<AttemptChat session={session} />);
    await enterMessage();
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));
    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    expect(screen.getByText(/Intento detenido por un control/)).toBeInTheDocument();
    await enterMessage("Consulta mi pedido A-1001");
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));
    await waitFor(() => expect(screen.getAllByText("Solicitud rechazada.")).toHaveLength(2));
    expect(
      within(screen.getByRole("list", { name: "Historial de intentos" })).getAllByRole("listitem"),
    ).toHaveLength(2);
    const posts = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(posts).toHaveLength(2);
    expect(posts[0]?.[1]?.headers).toEqual(
      expect.objectContaining({ Authorization: "Bearer signed-token" }),
    );
    expect(JSON.parse(String(posts[0]?.[1]?.body))).toMatchObject({
      messages: ["Consulta B-2001"],
      idempotency_key: expect.any(String),
    });
    expect(JSON.parse(String(posts[0]?.[1]?.body)).idempotency_key).not.toBe(
      JSON.parse(String(posts[1]?.[1]?.body)).idempotency_key,
    );
  });

  it("mantiene el payload y la idempotencia después de red fallida y recarga", async () => {
    let calls = 0;
    const mock = mockApi(async () => {
      if (++calls === 1) throw new TypeError("offline");
      return Response.json(attempt());
    });
    const first = render(<AttemptChat session={session} />);
    await enterMessage();
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));
    expect(await screen.findByRole("button", { name: "Reintentar envío" })).toBeInTheDocument();
    expect(loadHistory(session.id)[0]?.attempt).toBeNull();
    first.unmount();
    render(<AttemptChat session={session} />);
    await userEvent.click(await screen.findByRole("button", { name: "Reintentar envío" }));
    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    const posts = mock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(posts).toHaveLength(2);
    expect(posts[0]?.[1]?.body).toBe(posts[1]?.[1]?.body);
    expect(screen.getAllByRole("heading", { name: /Intento \d/ })).toHaveLength(1);
  });

  it("reconcilia una aceptación cuyo response se perdió sin volver a enviar", async () => {
    let remote: Attempt[] = [];
    const mock = mockApi(
      async (init) => {
        const body = JSON.parse(String(init.body));
        remote = [attempt({ idempotency_key: body.idempotency_key, messages: body.messages })];
        throw new TypeError("connection reset after acceptance");
      },
      async () => Response.json(remote),
    );
    render(<AttemptChat session={session} />);
    await enterMessage();
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));
    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reintentar envío" })).not.toBeInTheDocument();
    expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it("construye hasta cuatro turnos explícitos en una misma ejecución", async () => {
    const mock = mockApi(async () => Response.json(attempt()));
    render(<AttemptChat session={session} />);
    await enterMessage("Recuerda que prefiero español");
    for (const turn of [2, 3, 4]) {
      await userEvent.click(screen.getByRole("button", { name: "Añadir turno" }));
      await userEvent.type(screen.getByLabelText(`Mensaje ${turn}`), `Consulta de turno ${turn}`);
    }
    expect(screen.queryByRole("button", { name: "Añadir turno" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));
    await screen.findByText("Solicitud rechazada.");
    const post = mock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(JSON.parse(String(post?.[1]?.body)).messages).toEqual([
      "Recuerda que prefiero español",
      "Consulta de turno 2",
      "Consulta de turno 3",
      "Consulta de turno 4",
    ]);
  });

  it("impide envíos concurrentes incluso con dos submits en el mismo evento", async () => {
    const response = deferred<Response>();
    const mock = mockApi(() => response.promise);
    render(<AttemptChat session={session} />);
    await enterMessage();
    act(() => {
      fireEvent.submit(screen.getByRole("form", { name: "Nuevo intento" }));
      fireEvent.submit(screen.getByRole("form", { name: "Nuevo intento" }));
    });
    expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
    await act(async () => response.resolve(Response.json(attempt())));
    expect(screen.getAllByRole("heading", { name: /Intento \d/ })).toHaveLength(1);
  });

  it("recupera intentos en ejecución y conserva respuestas previas al desconectar", async () => {
    saveHistory(session.id, [
      {
        key: "old",
        messages: ["Anterior"],
        attempt: attempt({ id: "old", reply: "Respuesta anterior" }),
      },
    ]);
    mockApi(
      async () => Response.json(attempt()),
      async () =>
        Response.json([
          attempt({
            id: "running",
            status: "running",
            outcome: null,
            reply: "",
            messages: ["En ejecución"],
          }),
        ]),
    );
    render(<AttemptChat session={session} />);
    expect(await screen.findByText(/Ejecutándose · Política 1/)).toBeInTheDocument();
    expect(screen.getByText("Respuesta anterior")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Esperando resultado…" })).toBeDisabled();
  });

  it("respeta Retry-After sin regenerar la clave", async () => {
    mockApi(async () =>
      Response.json(
        { detail: "Límite de frecuencia" },
        { status: 429, headers: { "Retry-After": "60" } },
      ),
    );
    render(<AttemptChat session={session} />);
    await enterMessage();
    vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-10-24T12:00:00Z"));
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));
    expect(await screen.findByText("Límite de frecuencia")).toBeInTheDocument();
    // The wait comes from the header (60 s), not from the 5 s fallback.
    expect(await screen.findByRole("button", { name: "Reintentar en 60 s" })).toBeDisabled();
    expect(loadHistory(session.id)[0]?.key).toBeTruthy();
  });

  it("espera 5 s ante un 429 sin Retry-After", async () => {
    mockApi(async () => Response.json({ detail: "Cola llena" }, { status: 429 }));
    render(<AttemptChat session={session} />);
    await enterMessage();
    vi.spyOn(Date, "now").mockReturnValue(Date.parse("2026-10-24T12:00:00Z"));
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));
    expect(await screen.findByText("Cola llena")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Reintentar en 5 s" })).toBeDisabled();
    expect(loadHistory(session.id)[0]?.key).toBeTruthy();
  });

  it("solicita renovar una sesión invalidada y no muestra detalles de operación", async () => {
    const expired = vi.fn();
    mockApi(
      async () => Response.json(attempt()),
      async () => Response.json({ detail: "Sesión vencida" }, { status: 401 }),
    );
    render(<AttemptChat session={session} onExpired={expired} />);
    await waitFor(() => expect(expired).toHaveBeenCalledOnce());
    expect(screen.queryByText(/honeypot|cust-|AZP_|AZH_/i)).not.toBeInTheDocument();
  });

  it("reconcilia revelación final sin anticipar la ruta con datos desfasados", async () => {
    mockApi(
      async () => Response.json(attempt()),
      async () => Response.json([attempt({ outcome: "contained_honeypot" })]),
    );
    const first = render(<AttemptChat session={session} />);
    expect(await screen.findByText(/Objetivo aparentemente logrado/)).toBeInTheDocument();
    expect(screen.queryByText(/Éxito aparente en señuelo aislado/)).not.toBeInTheDocument();
    first.unmount();
    vi.restoreAllMocks();
    mockApi(
      async () => Response.json(attempt()),
      async () => Response.json([attempt({ outcome: "contained_honeypot" })]),
      { ...arena, revealed: true, provisional: false },
    );
    render(<AttemptChat session={session} />);
    expect(await screen.findByText(/Éxito aparente en señuelo aislado/)).toHaveTextContent(
      "sin efectos protegidos",
    );
  });

  it("una lectura vieja no devuelve un intento final a la cola", () => {
    const final = attempt();
    const merged = mergeHistory(
      [{ key: "stable", messages: ["Consulta"], attempt: final }],
      [attempt({ status: "queued", outcome: null, reply: "" })],
    );
    expect(merged).toHaveLength(1);
    expect(merged[0]?.attempt).toEqual(final);
  });

  it("cierra envío al pausar y mantiene el historial visible", async () => {
    mockApi(
      async () => Response.json(attempt()),
      async () => Response.json([attempt()]),
      { ...arena, accepting: false },
    );
    render(<AttemptChat session={session} />);
    expect(await screen.findByText(/Las entradas están cerradas/)).toBeInTheDocument();
    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar intento" })).toBeDisabled();
    expect(screen.getByLabelText("Mensaje al asistente")).toBeDisabled();
  });
});
