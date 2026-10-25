import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { arena, attempt, session } from "../../test/fixtures";
import { AttemptChat } from "./AttemptChat";
import type { Attempt } from "./types";

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
  it("deja escribir y juntar mensajes mientras Yummy responde, sin enviarlos", async () => {
    const spy = mockApi(() => [running]);
    render(<AttemptChat session={session} />);
    const box = screen.getByLabelText("Mensaje al asistente");
    expect(await screen.findByText(/Yummy está respondiendo/)).toBeInTheDocument();
    expect(box).toBeEnabled();
    await userEvent.type(box, "Siguiente{Shift>}{Enter}{/Shift}más");
    expect(box).toHaveValue("Siguiente\nmás");
    await userEvent.type(box, "{Enter}");
    expect(box).toHaveValue("");
    const pending = screen.getByRole("list", { name: "Mensajes por enviar" });
    expect(pending).toHaveTextContent(/Siguiente\s+más/);
    expect(pending).toHaveTextContent("Pendiente");
    expect(posts(spy)).toHaveLength(0);
  });

  it("«Enviar ahora» espera a que termine la respuesta y luego manda el lote", async () => {
    let done = false;
    const spy = mockApi(() => [
      done ? attempt({ id: "run", messages: ["Hola"], reply: "Listo" }) : running,
    ]);
    render(<AttemptChat session={session} />);
    const box = screen.getByLabelText("Mensaje al asistente");
    await screen.findByText(/Yummy está respondiendo/);
    await userEvent.type(box, "Mi segunda pregunta{Enter}");
    await userEvent.click(screen.getByRole("button", { name: "Enviar ahora" }));
    expect(screen.getByText(/Se envía cuando Yummy termine de responder/)).toBeInTheDocument();
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
