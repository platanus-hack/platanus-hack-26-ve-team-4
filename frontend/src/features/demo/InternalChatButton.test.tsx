import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { session } from "../../test/fixtures";
import { InternalChatButton } from "./InternalChatButton";

afterEach(() => vi.restoreAllMocks());

describe("InternalChatButton", () => {
  it("abre el diálogo y lanza los chats internos a la vez", async () => {
    let created = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input) === "/api/sessions") {
        created += 1;
        return Response.json({ ...session, id: `sess-${created}` });
      }
      return new Promise<Response>(() => {});
    });
    render(<InternalChatButton secret="s" />);
    fireEvent.click(screen.getByRole("button", { name: "Chat interno" }));
    fireEvent.click(screen.getByRole("button", { name: "Lanzar 6 chats" }));
    expect(await screen.findByRole("button", { name: /Detener chat interno/ })).toBeInTheDocument();
    await vi.waitFor(() => expect(created).toBe(6));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
