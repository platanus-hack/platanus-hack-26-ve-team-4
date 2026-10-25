import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Carousel } from "./Carousel";
import type { CarouselItem, ChatTone } from "./types";

const ids = ["1", "2", "3", "4", "5", "6", "7", "8"];
function item(id: string, tone: ChatTone = "attacking", pulseKey = "0"): CarouselItem {
  return { id, label: `Agente-${id}`, short: `A-${id}`, tone, title: `Agente-${id}`, pulseKey };
}

function carousel(pinned: string[] = [], items = ids.map((id) => item(id))) {
  return render(
    <Carousel
      items={items}
      pinned={pinned}
      scale={1}
      renderChat={(id, inView) => (
        <section key={id} className="av-chat" aria-label={`Chat ${id}`} inert={!inView} />
      )}
    />,
  );
}
const visible = () =>
  screen
    .getAllByRole("region", { name: /^Chat \d$/, hidden: true })
    .filter((chat) => !chat.hasAttribute("inert"))
    .map((chat) => chat.getAttribute("aria-label"));
const current = () =>
  screen
    .getAllByRole("button", { name: /^Ir al chat/ })
    .filter((button) => button.getAttribute("aria-current") === "true")
    .map((button) => button.textContent);

afterEach(() => vi.useRealTimers());

describe("Carousel", () => {
  it("muestra 8 indicadores, 3 chats a la vista y el resto inerte", () => {
    carousel();

    expect(screen.getAllByRole("button", { name: /^Ir al chat/ })).toHaveLength(8);
    expect(visible()).toEqual(["Chat 1", "Chat 2", "Chat 3"]);
    expect(current()).toEqual(["A-1", "A-2", "A-3"]);
    expect(screen.getByRole("button", { name: "Chat anterior" })).toBeDisabled();
    expect(document.querySelectorAll(".av-cframe")).toHaveLength(1);
  });

  it("avanza con las flechas del teclado y de la barra sin pasarse del final", async () => {
    carousel();
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(visible()).toEqual(["Chat 2", "Chat 3", "Chat 4"]);
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(visible()).toEqual(["Chat 1", "Chat 2", "Chat 3"]);

    const next = screen.getByRole("button", { name: "Chat siguiente" });
    for (let n = 0; n < 9; n++) if (!next.hasAttribute("disabled")) await userEvent.click(next);
    expect(visible()).toEqual(["Chat 6", "Chat 7", "Chat 8"]);
    expect(next).toBeDisabled();
  });

  it("no navega mientras se escribe en un campo", () => {
    render(<input aria-label="campo" />);
    carousel();
    fireEvent.keyDown(screen.getByLabelText("campo"), { key: "ArrowRight" });
    expect(visible()).toEqual(["Chat 1", "Chat 2", "Chat 3"]);
  });

  it("un indicador fuera de la ventana la centra en ese chat", async () => {
    carousel();
    await userEvent.click(screen.getByRole("button", { name: "Ir al chat 6: Agente-6" }));
    expect(visible()).toEqual(["Chat 5", "Chat 6", "Chat 7"]);
    await userEvent.click(screen.getByRole("button", { name: "Ir al chat 6: Agente-6" }));
    expect(visible()).toEqual(["Chat 5", "Chat 6", "Chat 7"]);
  });

  it("la rueda vertical pasa un chat por gesto", () => {
    carousel();
    const nav = screen.getByRole("navigation", { name: "Navegar entre chats" });
    fireEvent.wheel(nav, { deltaY: 120 });
    expect(visible()).toEqual(["Chat 2", "Chat 3", "Chat 4"]);
  });

  it("un arrastre corto basta para pasar al siguiente chat", () => {
    carousel();
    const view = document.querySelector(".av-cview") as HTMLElement;
    fireEvent.pointerDown(view, { pointerId: 1, button: 0, clientX: 500, pointerType: "mouse" });
    fireEvent.pointerMove(view, { pointerId: 1, clientX: 400, pointerType: "mouse" });
    fireEvent.pointerUp(view, { pointerId: 1, clientX: 400, pointerType: "mouse" });
    expect(visible()).toEqual(["Chat 2", "Chat 3", "Chat 4"]);
  });

  it("los fijados van a la izquierda y la ventana mueve solo el resto", () => {
    carousel(["5", "7"]);

    const order = screen
      .getAllByRole("button", { name: /^Ir al chat/ })
      .map((button) => button.textContent);
    expect(order.slice(0, 2)).toEqual(["A-5", "A-7"]);
    expect(visible()).toEqual(["Chat 5", "Chat 7", "Chat 1"]);
    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(visible()).toEqual(["Chat 5", "Chat 7", "Chat 2"]);
    expect(document.querySelectorAll(".av-ci.pinned")).toHaveLength(2);
    expect(document.querySelectorAll(".av-cframe")).toHaveLength(2);
  });

  it("el indicador marca el evento 4 s cuando cambia el pulso, sin cambiar de color", () => {
    vi.useFakeTimers();
    const first = ids.map((id) => item(id));
    const { rerender } = carousel([], first);
    const later = first.map((entry) => (entry.id === "2" ? { ...entry, pulseKey: "1" } : entry));
    rerender(
      <Carousel
        items={later}
        pinned={[]}
        scale={1}
        renderChat={(id) => <section key={id} aria-label={`Chat ${id}`} />}
      />,
    );
    const indicator = screen.getByRole("button", { name: "Ir al chat 2: Agente-2" });
    expect(indicator).toHaveClass("evt", "st-attacking");
    act(() => vi.advanceTimersByTime(4000));
    expect(indicator).not.toHaveClass("evt");
  });
});
