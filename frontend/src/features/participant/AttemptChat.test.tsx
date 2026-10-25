import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { arena, attempt, deferred, session } from "../../test/fixtures";
import { AttemptChat, greetingName, mergeHistory } from "./AttemptChat";
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
function results() {
  return within(screen.getByRole("list", { name: "Resultados por mensaje" })).getAllByRole(
    "listitem",
  );
}
async function enterMessage(text = "Consulta B-2001") {
  await userEvent.type(screen.getByLabelText("Mensaje al asistente"), text);
  await waitFor(() => expect(screen.getByRole("button", { name: "Enviar" })).not.toBeDisabled());
}
// El mensaje sale en el momento: no hay contador ni «Enviar ahora».
async function send() {
  await userEvent.click(screen.getByRole("button", { name: "Enviar" }));
}

describe("greetingName", () => {
  it("saluda con el alias y sin el prefijo del chat de prueba", () => {
    expect(greetingName("neo")).toBe("neo");
    expect(greetingName("Interno-Fer")).toBe("Fer");
    expect(greetingName("Interno-")).toBe("Interno-");
  });
});

describe("AttemptChat", () => {
  it("saluda con el alias, no con la identidad ficticia", async () => {
    mockApi(async () => Response.json(attempt()));
    render(<AttemptChat session={session} />);
    expect(await screen.findByText(/¡Hola, neo!/)).toBeInTheDocument();
    expect(screen.queryByText(/¡Hola, Ana!/)).toBeNull();
  });

  it("envía con token y clave estable, conserva conversación y permite varios intentos", async () => {
    let number = 0;
    const fetchMock = mockApi(async () =>
      Response.json(attempt({ id: `attempt-${++number}` }), { status: 202 }),
    );
    render(<AttemptChat session={session} />);
    await enterMessage();
    await send();
    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    expect(screen.getByText(/Interacción detenida por un control/)).toBeInTheDocument();
    await enterMessage("Consulta mi pedido A-1001");
    await send();
    await waitFor(() => expect(screen.getAllByText("Solicitud rechazada.")).toHaveLength(2));
    expect(results()).toHaveLength(2);
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
    expect(JSON.parse(String(posts[0]?.[1]?.body)).continues).toBeNull();
    expect(JSON.parse(String(posts[1]?.[1]?.body)).continues).toBe("attempt-1");
  });

  it("mantiene el payload y la idempotencia después de red fallida y recarga", async () => {
    let calls = 0;
    const mock = mockApi(async () => {
      if (++calls === 1) throw new TypeError("offline");
      return Response.json(attempt());
    });
    const first = render(<AttemptChat session={session} />);
    await enterMessage();
    await send();
    expect(await screen.findByRole("button", { name: "Reintentar envío" })).toBeInTheDocument();
    expect(loadHistory(session.id)[0]?.attempt).toBeNull();
    first.unmount();
    render(<AttemptChat session={session} />);
    await userEvent.click(await screen.findByRole("button", { name: "Reintentar envío" }));
    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    const posts = mock.mock.calls.filter(([, init]) => init?.method === "POST");
    expect(posts).toHaveLength(2);
    expect(posts[0]?.[1]?.body).toBe(posts[1]?.[1]?.body);
    expect(results()).toHaveLength(1);
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
    await send();
    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reintentar envío" })).not.toBeInTheDocument();
    expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it("«Nueva conversación» corta el contexto y lo marca en el chat", async () => {
    let number = 0;
    const mock = mockApi(async () =>
      Response.json(attempt({ id: `attempt-${++number}` }), { status: 202 }),
    );
    render(<AttemptChat session={session} />);
    await enterMessage("Hola");
    await send();
    await screen.findByText("Solicitud rechazada.");
    await userEvent.click(screen.getByRole("button", { name: "Nueva conversación" }));
    await enterMessage("Otra consulta");
    await send();
    await waitFor(() => expect(screen.getAllByText("Solicitud rechazada.")).toHaveLength(2));
    const bodies = mock.mock.calls
      .filter(([, init]) => init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)));
    expect(bodies.map((body) => body.continues)).toEqual([null, null]);
    expect(screen.getByText("Nueva conversación", { selector: ".chat-divider" })).toBeVisible();
  });

  it("si la conversación ya no se puede continuar, devuelve el texto y abre una nueva", async () => {
    saveHistory(session.id, [
      { key: "old", messages: ["Hola"], attempt: attempt({ id: "old" }), continues: null },
    ]);
    let calls = 0;
    const mock = mockApi(async () =>
      ++calls === 1
        ? Response.json({ detail: "La conversación llegó a su largo máximo" }, { status: 409 })
        : Response.json(attempt({ id: "new" }), { status: 202 }),
    );
    render(<AttemptChat session={session} />);
    await enterMessage("Sigo aquí");
    await send();
    expect(await screen.findByRole("alert")).toHaveTextContent("largo máximo");
    await waitFor(() =>
      expect(screen.getByLabelText("Mensaje al asistente")).toHaveValue("Sigo aquí"),
    );
    await send();
    await waitFor(() => expect(results()).toHaveLength(2));
    const bodies = mock.mock.calls
      .filter(([, init]) => init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)));
    expect(bodies.map((body) => body.continues)).toEqual(["old", null]);
  });

  it("impide envíos concurrentes incluso con dos submits en el mismo evento", async () => {
    const response = deferred<Response>();
    const mock = mockApi(() => response.promise);
    render(<AttemptChat session={session} />);
    await enterMessage();
    act(() => {
      fireEvent.submit(screen.getByRole("form", { name: "Nuevo mensaje" }));
      fireEvent.submit(screen.getByRole("form", { name: "Nuevo mensaje" }));
    });
    await waitFor(() =>
      expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1),
    );
    await act(async () => response.resolve(Response.json(attempt())));
    expect(results()).toHaveLength(1);
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
    expect(screen.getByText("Escribiendo…")).toBeInTheDocument();
    expect(screen.getByLabelText("Mensaje al asistente")).toBeEnabled();
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
    await send();
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
    await send();
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

  it("la reconciliación conserva las partes de un lote enviado como un solo mensaje", () => {
    const merged = mergeHistory(
      [{ key: "lote", messages: ["uno\ndos"], parts: ["uno", "dos"], attempt: null }],
      [attempt({ idempotency_key: "lote", messages: ["uno\ndos"] })],
    );
    expect(merged).toHaveLength(1);
    expect(merged[0]).toMatchObject({ messages: ["uno\ndos"], parts: ["uno", "dos"] });
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
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
    expect(screen.getByLabelText("Mensaje al asistente")).toBeDisabled();
  });
});
