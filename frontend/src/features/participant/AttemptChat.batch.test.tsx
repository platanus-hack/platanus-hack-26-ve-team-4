import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { arena, attempt, session } from "../../test/fixtures";
import { AttemptChat } from "./AttemptChat";
import { loadBatch } from "./storage";
import type { ArenaSession, Attempt } from "./types";

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
async function open(value: ArenaSession = session) {
  const view = render(<AttemptChat session={value} />);
  await advance(0);
  await advance(0);
  return view;
}
function write(text: string) {
  fireEvent.change(screen.getByLabelText("Mensaje al asistente"), { target: { value: text } });
  fireEvent.submit(screen.getByRole("form", { name: "Nuevo mensaje" }));
}
const pending = () => screen.queryByRole("list", { name: "Mensajes por enviar" });
const countdown = () => screen.getByRole("timer");

describe("AttemptChat lote de mensajes", () => {
  beforeEach(() => {
    vi.useFakeTimers({
      toFake: ["setTimeout", "clearTimeout", "setInterval", "clearInterval", "Date"],
    });
    vi.setSystemTime(Date.parse("2026-10-25T12:00:00Z"));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("muestra el mensaje como pendiente y espera 10 s; cada mensaje nuevo reinicia la espera", async () => {
    const spy = mockApi();
    await open();
    write("uno");
    expect(within(pending() as HTMLElement).getByText("uno")).toBeInTheDocument();
    expect(pending()).toHaveTextContent("Pendiente");
    expect(screen.getByLabelText("Mensaje al asistente")).toHaveValue("");
    expect(countdown()).toHaveTextContent("1 mensaje pendiente. Se envía en 10 s");
    await advance(9_000);
    expect(countdown()).toHaveTextContent("Se envía en 1 s");
    write("dos");
    expect(countdown()).toHaveTextContent("2 mensajes pendientes. Se envía en 10 s");
    await advance(9_000);
    expect(bodies(spy)).toHaveLength(0);
    await advance(1_000);
    expect(bodies(spy)).toHaveLength(1);
    expect(bodies(spy)[0]).toMatchObject({ messages: ["uno\ndos"], continues: null });
    expect(pending()).toBeNull();
    expect(loadBatch(session.id)).toBeNull();
    // En el chat siguen siendo dos burbujas, aunque viajaron como un solo mensaje.
    const thread = screen.getByRole("list", { name: "Conversación" });
    expect(within(thread).getByText("uno")).toBeInTheDocument();
    expect(within(thread).getByText("dos")).toBeInTheDocument();
  });

  it("envía a los 20 s del primer mensaje aunque se siga escribiendo", async () => {
    const spy = mockApi();
    await open();
    write("uno");
    await advance(8_000);
    write("dos");
    await advance(8_000);
    write("tres");
    expect(countdown()).toHaveTextContent("Se envía en 4 s");
    await advance(3_900);
    expect(bodies(spy)).toHaveLength(0);
    await advance(100);
    expect(bodies(spy).map((body) => body.messages)).toEqual([["uno\ndos\ntres"]]);
  });

  it("envía al juntar el cuarto mensaje sin esperar el contador", async () => {
    const spy = mockApi();
    await open();
    for (const text of ["uno", "dos", "tres"]) write(text);
    await advance(0);
    expect(bodies(spy)).toHaveLength(0);
    write("cuatro");
    await advance(0);
    expect(bodies(spy).map((body) => body.messages)).toEqual([["uno\ndos\ntres\ncuatro"]]);
  });

  it("«Enviar ahora» manda el lote en el momento", async () => {
    const spy = mockApi();
    await open();
    write("uno");
    write("dos");
    fireEvent.click(screen.getByRole("button", { name: "Enviar ahora" }));
    await advance(0);
    expect(bodies(spy).map((body) => body.messages)).toEqual([["uno\ndos"]]);
    expect(screen.queryByRole("button", { name: "Enviar ahora" })).toBeNull();
  });

  it("si unidos superan el largo máximo, los envía como lista de mensajes", async () => {
    const spy = mockApi();
    await open({
      ...session,
      limits: { attempts_per_minute: 12, max_messages: 4, message_max_length: 10 },
    });
    write("123456");
    write("abcdef");
    fireEvent.click(screen.getByRole("button", { name: "Enviar ahora" }));
    await advance(0);
    expect(bodies(spy).map((body) => body.messages)).toEqual([["123456", "abcdef"]]);
  });

  it("mientras Yummy responde, los mensajes arman el lote siguiente y esperan su turno", async () => {
    let done = false;
    const spy = mockApi(() => [
      attempt(
        done
          ? { id: "run", messages: ["Hola"], reply: "Listo" }
          : { id: "run", status: "running", outcome: null, reply: "", messages: ["Hola"] },
      ),
    ]);
    await open();
    expect(screen.getByText(/Yummy está respondiendo/)).toBeInTheDocument();
    write("sigo");
    write("escribiendo");
    await advance(10_000);
    expect(bodies(spy)).toHaveLength(0);
    expect(countdown()).toHaveTextContent("Se envía cuando Yummy termine de responder");
    expect(screen.getByRole("button", { name: "Enviar ahora" })).toBeDisabled();
    done = true;
    await advance(1_500);
    await advance(0);
    expect(bodies(spy)).toEqual([
      expect.objectContaining({ messages: ["sigo\nescribiendo"], continues: "run" }),
    ]);
  });

  it("con el lote lleno mientras Yummy responde, no admite un quinto mensaje", async () => {
    const spy = mockApi(() => [
      attempt({ id: "run", status: "running", outcome: null, reply: "", messages: ["Hola"] }),
    ]);
    await open();
    for (const text of ["uno", "dos", "tres", "cuatro", "cinco"]) write(text);
    expect(within(pending() as HTMLElement).getAllByRole("listitem")).toHaveLength(4);
    expect(screen.getByLabelText("Mensaje al asistente")).toHaveValue("cinco");
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
    expect(screen.getByText(/Ya juntaste el máximo de mensajes/)).toBeInTheDocument();
    expect(bodies(spy)).toHaveLength(0);
  });

  it("un lote sin enviar sobrevive a una recarga y sale al vencer", async () => {
    const spy = mockApi();
    const first = await open();
    write("antes de recargar");
    first.unmount();
    expect(loadBatch(session.id)?.texts).toEqual(["antes de recargar"]);
    await advance(4_000);
    await open();
    expect(within(pending() as HTMLElement).getByText("antes de recargar")).toBeInTheDocument();
    expect(countdown()).toHaveTextContent("Se envía en 6 s");
    await advance(6_000);
    expect(bodies(spy).map((body) => body.messages)).toEqual([["antes de recargar"]]);
  });
});
