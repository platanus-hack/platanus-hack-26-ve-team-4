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
  it("permite redactar, bloquea Enter y Enviar, y muestra el indicador", async () => {
    const spy = mockApi(() => [running]);
    render(<AttemptChat session={session} />);
    const box = screen.getByLabelText("Mensaje al asistente");
    expect(await screen.findByText(/Yummy está respondiendo/)).toBeInTheDocument();
    expect(box).toBeEnabled();
    await userEvent.type(box, "Siguiente{Enter}");
    expect(box).toHaveValue("Siguiente");
    expect(screen.getByRole("button", { name: "Esperando respuesta…" })).toBeDisabled();
    expect(posts(spy)).toHaveLength(0);
    await userEvent.type(box, "{Shift>}{Enter}{/Shift}más");
    expect(box).toHaveValue("Siguiente\nmás");
  });

  it("conserva el borrador y lo envía al llegar la respuesta; el indicador desaparece", async () => {
    let done = false;
    const spy = mockApi(() => [
      done ? attempt({ id: "run", messages: ["Hola"], reply: "Listo" }) : running,
    ]);
    render(<AttemptChat session={session} />);
    const box = screen.getByLabelText("Mensaje al asistente");
    await screen.findByText(/Yummy está respondiendo/);
    await userEvent.type(box, "Mi segunda pregunta");
    done = true;
    await waitFor(() => expect(screen.queryByText(/Yummy está respondiendo/)).toBeNull(), {
      timeout: 4000,
    });
    expect(box).toHaveValue("Mi segunda pregunta");
    await userEvent.type(box, "{Enter}");
    await waitFor(() => expect(posts(spy)).toHaveLength(1));
    expect(JSON.parse(String(posts(spy)[0]?.[1]?.body)).messages).toEqual(["Mi segunda pregunta"]);
    expect(box).toHaveValue("");
  });
});
