import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { arena, attempt, session } from "../../test/fixtures";
import { AttemptChat } from "./AttemptChat";
import { loadBatch } from "./storage";
import type { Attempt } from "./types";

function mockApi(history: () => Attempt[] = () => []) {
  let number = 0;
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (path === "/api/arena/state") return Response.json(arena);
    if (path === "/api/attempts" && init?.method === "POST") {
      return Response.json(attempt({ id: `attempt-${++number}` }), { status: 202 });
    }
    if (path === "/api/attempts") return Response.json(history());
    throw new Error(`Unexpected request ${path}`);
  });
}
const bodies = (spy: ReturnType<typeof mockApi>) =>
  spy.mock.calls
    .filter(([, init]) => init?.method === "POST")
    .map(([, init]) => JSON.parse(String(init?.body)));

/** Avanza el reloj falso y deja correr las promesas del fetch simulado. */
async function advance(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}
async function open() {
  const view = render(<AttemptChat session={session} />);
  await advance(0);
  await advance(0);
  return view;
}
function write(text: string) {
  fireEvent.change(screen.getByLabelText("Mensaje al asistente"), { target: { value: text } });
  fireEvent.submit(screen.getByRole("form", { name: "Nuevo mensaje" }));
}
const queued = () => screen.queryByRole("list", { name: "Mensajes por enviar" });
const running = () =>
  attempt({ id: "run", status: "running", outcome: null, reply: "", messages: ["Hola"] });
const answered = () => attempt({ id: "run", messages: ["Hola"], reply: "Listo" });

describe("AttemptChat envío directo", () => {
  beforeEach(() => {
    vi.useFakeTimers({
      toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"],
    });
    vi.setSystemTime(Date.parse("2026-10-25T12:00:00Z"));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("envía el mensaje en el momento, sin contador ni marca de pendiente", async () => {
    const spy = mockApi();
    await open();
    write("uno");
    await advance(0);
    expect(bodies(spy)).toEqual([expect.objectContaining({ messages: ["uno"], continues: null })]);
    expect(screen.queryByRole("timer")).toBeNull();
    expect(screen.queryByText("Pendiente")).toBeNull();
    expect(screen.queryByRole("button", { name: "Enviar ahora" })).toBeNull();
    expect(loadBatch(session.id)).toBeNull();
  });

  it("mientras Yummy responde, los mensajes se ven enviados y salen juntos al terminar", async () => {
    let done = false;
    const spy = mockApi(() => [done ? answered() : running()]);
    await open();
    expect(screen.queryByText(/Yummy está respondiendo/)).toBeNull();
    write("sigo");
    write("escribiendo");
    await advance(10_000);
    expect(bodies(spy)).toHaveLength(0);
    expect(within(queued() as HTMLElement).getByText("sigo")).toBeInTheDocument();
    expect(queued()).not.toHaveTextContent("Pendiente");
    done = true;
    await advance(1_500);
    await advance(0);
    expect(bodies(spy)).toEqual([
      expect.objectContaining({ messages: ["sigo\nescribiendo"], continues: "run" }),
    ]);
    expect(queued()).toBeNull();
  });

  it("con 10 mensajes sin respuesta pide esperar a Yummy y no admite el siguiente", async () => {
    const spy = mockApi(() => [running()]);
    await open();
    for (let n = 1; n <= 11; n += 1) write(`mensaje ${n}`);
    expect(within(queued() as HTMLElement).getAllByRole("listitem")).toHaveLength(10);
    expect(screen.getByLabelText("Mensaje al asistente")).toHaveValue("mensaje 11");
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
    expect(screen.getByText(/Espera unos segundos a que Yummy responda/)).toBeInTheDocument();
    expect(bodies(spy)).toHaveLength(0);
  });

  it("una cola sin enviar sobrevive a una recarga y sale al recuperar la sesión", async () => {
    let done = false;
    const spy = mockApi(() => [done ? answered() : running()]);
    const first = await open();
    write("antes de recargar");
    first.unmount();
    expect(loadBatch(session.id)?.texts).toEqual(["antes de recargar"]);
    done = true;
    await open();
    await advance(0);
    expect(bodies(spy).map((body) => body.messages)).toEqual([["antes de recargar"]]);
  });
});
