import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { session } from "../../test/fixtures";
import { board, liveAttempt, liveSession } from "../board/fixtures";
import { DemoPage } from "./DemoPage";

afterEach(() => vi.restoreAllMocks());

describe("DemoPage", () => {
  it("lanza los chats a la vez y muestra la ruta y el veredicto de cada uno", async () => {
    let created = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/api/sessions") {
        created += 1;
        return Response.json({ ...session, id: `sess-${created}` });
      }
      if (url.startsWith("/api/operator/live"))
        return Response.json(
          board([
            liveSession("sess-1", {
              kind: "test",
              attempts: [liveAttempt({ id: "att-sess-1", route: "honeypot", reply: "Te ayudo." })],
            }),
          ]),
        );
      if (init?.method === "POST")
        return Response.json({ id: "att-sess-1", status: "queued", reply: "" });
      return Response.json({ id: "att-sess-1", status: "evaluated", reply: "Te ayudo." });
    });
    render(<DemoPage />);
    fireEvent.change(screen.getByLabelText("Secreto de operador"), { target: { value: "s" } });
    fireEvent.click(screen.getByRole("button", { name: "Acceder" }));
    fireEvent.click(screen.getByRole("button", { name: "Lanzar chats automáticos" }));
    fireEvent.change(screen.getByLabelText("¿Cuántos chats a la vez?"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Lanzar 1 chat" }));
    const chat = await screen.findByRole("article");
    expect(await within(chat).findByText("Señuelo", {}, { timeout: 4000 })).toBeInTheDocument();
    expect(within(chat).getByText(/Falso positivo/)).toBeInTheDocument();
    expect(screen.getByLabelText("Resultado en vivo")).toHaveTextContent("1falsos positivos");
  });
});
