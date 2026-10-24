import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { arena, session } from "../../test/fixtures";
import { ParticipantPage } from "./ParticipantPage";
import { loadSession, saveSession } from "./storage";

function mockFetch(handler: (path: string) => Response | Promise<Response>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path === "/api/arena/state") return Response.json(arena);
    if (path === "/api/attempts") return Response.json([]);
    return handler(path);
  });
}
async function login() {
  await userEvent.type(screen.getByLabelText("Alias"), "neo");
  await userEvent.click(screen.getByRole("checkbox"));
  await userEvent.click(screen.getByRole("button", { name: "Entrar a la arena" }));
}

describe("ParticipantPage", () => {
  it("crea la sesión con consentimiento y guarda credencial para recargar", async () => {
    const fetchMock = mockFetch(() => Response.json(session, { status: 201 }));
    render(<ParticipantPage />);
    await login();
    expect(await screen.findByRole("heading", { name: "Hola, neo" })).toBeInTheDocument();
    expect(loadSession()?.token).toBe("signed-token");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sessions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ alias: "neo", accepted_rules: true }),
      }),
    );
  });

  it("muestra el motivo del servidor al rechazar una sesión", async () => {
    mockFetch(() => Response.json({ detail: "La ronda está llena." }, { status: 409 }));
    render(<ParticipantPage />);
    await login();
    expect(await screen.findByRole("alert")).toHaveTextContent("La ronda está llena.");
  });

  it("no envía sin consentimiento", async () => {
    const fetchMock = mockFetch(() => Response.json(session));
    render(<ParticipantPage />);
    await userEvent.type(screen.getByLabelText("Alias"), "neo");
    expect(screen.getByRole("button", { name: "Entrar a la arena" })).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("revalida el token y recupera la sesión sin crear otra identidad", async () => {
    saveSession(session);
    const mock = mockFetch(() =>
      Response.json({ ...session, customer_name: "Identidad recuperada" }),
    );
    render(<ParticipantPage />);
    expect(await screen.findByRole("heading", { name: "Hola, neo" })).toBeInTheDocument();
    expect(screen.getByText("Identidad recuperada")).toBeInTheDocument();
    expect(mock).toHaveBeenCalledWith(
      "/api/sessions/me",
      expect.objectContaining({ headers: { Authorization: "Bearer signed-token" } }),
    );
    expect(mock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("limpia sesión inválida después de reset y vuelve a la entrada", async () => {
    saveSession(session);
    mockFetch(() => Response.json({ detail: "Sesión inválida" }, { status: 401 }));
    render(<ParticipantPage />);
    expect(await screen.findByLabelText("Alias")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("comenzó otra ronda");
    expect(loadSession()).toBeNull();
  });

  it("conserva el token ante fallo de red y permite recuperar después", async () => {
    saveSession(session);
    let connected = false;
    mockFetch(() => {
      if (!connected) throw new TypeError("offline");
      return Response.json(session);
    });
    render(<ParticipantPage />);
    await screen.findByRole("alert");
    expect(loadSession()?.token).toBe(session.token);
    connected = true;
    await userEvent.click(screen.getByRole("button", { name: "Volver a conectar" }));
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Hola, neo" })).toBeInTheDocument(),
    );
  });
});
