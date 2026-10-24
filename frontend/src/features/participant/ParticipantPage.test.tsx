import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ParticipantPage } from "./ParticipantPage";

function mockFetch(response: Response) {
  return vi.spyOn(globalThis, "fetch").mockResolvedValue(response);
}

describe("ParticipantPage", () => {
  it("crea la sesión con el alias y saluda al participante", async () => {
    const fetchMock = mockFetch(
      Response.json(
        {
          id: "sess-1",
          alias: "neo",
          created_at: "2026-10-24T00:00:00Z",
          token: "signed",
          expires_at: "2026-10-24T01:00:00Z",
          customer_name: "Ana",
          order_ids: ["A-1001"],
          objectives: [],
        },
        { status: 201 },
      ),
    );
    render(<ParticipantPage />);

    await userEvent.type(screen.getByLabelText("Alias"), "neo");
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Entrar a la arena" }));

    expect(await screen.findByRole("heading", { name: "Hola, neo" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sessions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ alias: "neo", accepted_rules: true }),
      }),
    );
  });

  it("muestra un error si la API rechaza la sesión", async () => {
    mockFetch(new Response(null, { status: 422 }));
    render(<ParticipantPage />);

    await userEvent.type(screen.getByLabelText("Alias"), "neo");
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: "Entrar a la arena" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos crear tu sesión");
  });
});
