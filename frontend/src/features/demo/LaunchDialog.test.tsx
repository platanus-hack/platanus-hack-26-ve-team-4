import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RECOMMENDED } from "./catalog";
import { LaunchDialog } from "./LaunchDialog";

describe("LaunchDialog", () => {
  it("lanza los 6 recomendados por defecto", () => {
    const onLaunch = vi.fn();
    render(<LaunchDialog onLaunch={onLaunch} onClose={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "Lanzar 6 chats" }));
    expect(onLaunch).toHaveBeenCalledWith(RECOMMENDED);
  });

  it("permite elegir cuántos chats y qué caso lleva cada uno", () => {
    const onLaunch = vi.fn();
    render(<LaunchDialog onLaunch={onLaunch} onClose={() => {}} />);
    fireEvent.change(screen.getByLabelText("¿Cuántos chats a la vez?"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Chat 2"), { target: { value: "N5-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Lanzar 2 chats" }));
    expect(onLaunch).toHaveBeenCalledWith(["N0-2", "N5-1"]);
  });
});
