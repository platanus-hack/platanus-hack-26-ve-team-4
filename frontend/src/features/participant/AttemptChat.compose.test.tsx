import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { arena, attempt, session } from "../../test/fixtures";
import { AttemptChat } from "./AttemptChat";
import type { Attempt } from "./types";

// Sin la espera del lote: estas pruebas usan reloj real y miran el envío, no la ventana de 10 s.
vi.mock("./batch", async (original) => ({
  ...(await original<typeof import("./batch")>()),
  BATCH_IDLE_MS: 0,
  TYPING_DELAY_MS: 0,
}));

const running = attempt({
  id: "run",
  status: "running",
  outcome: null,
  reply: "",
  messages: ["Hola"],
});

function mockApi(history: () => Attempt[]) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (path === "/api/arena/state") return Response.json(arena);
    if (path === "/api/attempts" && init?.method === "POST") {
      return Response.json(attempt({ id: "next" }), { status: 202 });
    }
    if (path === "/api/attempts") return Response.json(history());
    throw new Error(`Unexpected request ${path}`);
  });
}
const posts = (spy: ReturnType<typeof mockApi>) =>
  spy.mock.calls.filter(([, init]) => init?.method === "POST");

describe("AttemptChat redacción durante la espera", () => {
  it("deja escribir mientras Yummy responde y muestra el mensaje como enviado", async () => {
    const spy = mockApi(() => [running]);
    render(<AttemptChat session={session} />);
    const box = screen.getByLabelText("Mensaje al asistente");
    expect(await screen.findByText("Escribiendo…")).toBeInTheDocument();
    expect(box).toBeEnabled();
    await userEvent.type(box, "Siguiente{Shift>}{Enter}{/Shift}más");
    expect(box).toHaveValue("Siguiente\nmás");
    await userEvent.type(box, "{Enter}");
    expect(box).toHaveValue("");
    const queued = screen.getByRole("list", { name: "Mensajes por enviar" });
    expect(queued).toHaveTextContent(/Siguiente\s+más/);
    expect(queued).not.toHaveTextContent("Pendiente");
    expect(posts(spy)).toHaveLength(0);
  });

  it("al terminar la respuesta manda lo escrito sin que el participante haga nada", async () => {
    let done = false;
    const spy = mockApi(() => [
      done ? attempt({ id: "run", messages: ["Hola"], reply: "Listo" }) : running,
    ]);
    render(<AttemptChat session={session} />);
    const box = screen.getByLabelText("Mensaje al asistente");
    await screen.findByText("Escribiendo…");
    await userEvent.type(box, "Mi segunda pregunta{Enter}");
    expect(posts(spy)).toHaveLength(0);
    done = true;
    await waitFor(() => expect(posts(spy)).toHaveLength(1), { timeout: 4000 });
    expect(JSON.parse(String(posts(spy)[0]?.[1]?.body))).toMatchObject({
      messages: ["Mi segunda pregunta"],
      continues: "run",
    });
    expect(screen.queryByRole("list", { name: "Mensajes por enviar" })).toBeNull();
  });
});
