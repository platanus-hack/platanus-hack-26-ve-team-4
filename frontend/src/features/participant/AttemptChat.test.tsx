import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AttemptChat } from "./AttemptChat";

describe("AttemptChat", () => {
  it("envía con el token y muestra el veredicto del intento", async () => {
    const queued = {
      id: "attempt-1",
      status: "queued",
      outcome: null,
      reply: "",
      policy_version: 1,
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json(queued, { status: 202 }))
      .mockResolvedValueOnce(
        Response.json({
          ...queued,
          status: "evaluated",
          outcome: "prevented",
          reply: "Solicitud rechazada.",
        }),
      );
    render(
      <AttemptChat
        session={{
          id: "sess-1",
          alias: "neo",
          token: "signed-token",
          created_at: "",
          expires_at: "",
          customer_name: "Ana",
          order_ids: ["A-1001"],
          objectives: [],
        }}
      />,
    );
    await userEvent.type(screen.getByLabelText("Mensaje al asistente"), "Consulta B-2001");
    await userEvent.click(screen.getByRole("button", { name: "Enviar intento" }));
    expect(await screen.findByText("Solicitud rechazada.")).toBeInTheDocument();
    expect(screen.getByText(/Intento detenido por un control/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/attempts",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer signed-token" }),
      }),
    );
  });
});
