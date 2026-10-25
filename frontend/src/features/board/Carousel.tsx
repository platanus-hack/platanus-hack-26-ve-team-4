import { type PointerEvent, type ReactNode, useEffect, useRef, useState } from "react";
import { PinIcon } from "./ChatTile";
import { focusIndex, frames, STEP, windowOf } from "./slots";
import type { CarouselItem } from "./types";

const EVENT_MS = 4000;
const WHEEL_STEP = 40;
const WHEEL_LOCK_MS = 320;
const DRAG_START = 6;

interface Props {
  items: CarouselItem[];
  /** Fijados, del más antiguo al más nuevo. Van a la izquierda y no se mueven. */
  pinned: readonly string[];
  /** Escala del escenario: el arrastre se mide en píxeles del escenario. */
  scale: number;
  renderChat: (id: string, inView: boolean) => ReactNode;
}

const reducedMotion = () =>
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const isTyping = (target: EventTarget | null) =>
  target instanceof HTMLElement &&
  (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName));

/** Marca durante 4 s los indicadores cuyo `pulseKey` cambió (anillo de evento). */
function usePulses(items: CarouselItem[]): ReadonlySet<string> {
  const seen = useRef(new Map<string, string>());
  const [active, setActive] = useState<ReadonlySet<string>>(new Set());
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());
  useEffect(() => {
    const changed: string[] = [];
    for (const item of items) {
      const before = seen.current.get(item.id);
      if (before !== undefined && before !== item.pulseKey) changed.push(item.id);
      seen.current.set(item.id, item.pulseKey);
    }
    if (!changed.length) return;
    setActive((current) => new Set([...current, ...changed]));
    for (const id of changed) {
      clearTimeout(timers.current.get(id));
      timers.current.set(
        id,
        setTimeout(() => {
          setActive((current) => {
            const next = new Set(current);
            next.delete(id);
            return next;
          });
        }, EVENT_MS),
      );
    }
  }, [items]);
  useEffect(() => {
    const pending = timers.current;
    return () => {
      for (const timer of pending.values()) clearTimeout(timer);
    };
  }, []);
  return active;
}

export function Carousel({ items, pinned, scale, renderChat }: Props) {
  const ids = items.map((item) => item.id);
  const [index, setIndex] = useState(0);
  const win = windowOf(ids, pinned, index);
  const { start, maxIndex, slots, free, visible, order } = win;
  const view = useRef<HTMLDivElement>(null);
  const nav = useRef<HTMLElement>(null);
  const target = useRef<number | null>(null);
  const drag = useRef<{ x: number; y: number; left: number; id: number; on: boolean } | null>(null);
  const suppressClick = useRef(false);
  const pulses = usePulses(items);
  const goTo = useRef((next: number) => setIndex(next));
  goTo.current = (next: number) => setIndex(Math.max(0, Math.min(maxIndex, next)));

  // Mueve la ventana a `start`; el snap se apaga mientras dura el desplazamiento propio.
  useEffect(() => {
    const element = view.current;
    if (!element) return;
    const left = start * STEP;
    if (Math.abs(element.scrollLeft - left) < 1) return;
    target.current = left;
    const smooth = !reducedMotion() && typeof element.scrollTo === "function";
    element.classList.add("nosnap");
    if (smooth) element.scrollTo({ left, behavior: "smooth" });
    else element.scrollLeft = left;
    const done = setTimeout(
      () => {
        element.scrollLeft = left;
        target.current = null;
        element.classList.remove("nosnap");
      },
      smooth ? 600 : 0,
    );
    return () => clearTimeout(done);
  }, [start]);

  // Teclas ← y → (salvo mientras se escribe en un campo).
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (isTyping(event.target) || event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key === "ArrowRight") goTo.current(start + 1);
      else if (event.key === "ArrowLeft") goTo.current(start - 1);
      else return;
      event.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [start]);

  // Rueda sobre los chats: la vertical es de la conversación (el carrusel no se mueve). El carrusel se mueve con deltaX del trackpad (nativo con snap) o con Shift+rueda; sobre la barra, la rueda vertical sigue pasando un chat por gesto.
  useEffect(() => {
    let accumulated = 0;
    let lockUntil = 0;
    const onWheel = (event: WheelEvent) => {
      const horizontal = Math.abs(event.deltaX) > Math.abs(event.deltaY);
      if (event.currentTarget === view.current) {
        if (horizontal) return; // trackpad horizontal: scroll nativo
        if (!event.shiftKey) return; // rueda vertical: la recibe la conversación; nunca el carrusel
      }
      event.preventDefault();
      const now = Date.now();
      if (now < lockUntil) return;
      accumulated += horizontal ? event.deltaX : event.deltaY;
      if (Math.abs(accumulated) >= WHEEL_STEP) {
        goTo.current(start + Math.sign(accumulated));
        accumulated = 0;
        lockUntil = now + WHEEL_LOCK_MS;
      }
    };
    const targets = [view.current, nav.current].filter((node) => node !== null);
    for (const node of targets) node.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      for (const node of targets) node.removeEventListener("wheel", onWheel);
    };
  }, [start]);

  function onScroll() {
    const element = view.current;
    if (!element || drag.current?.on) return;
    if (target.current !== null) {
      if (Math.abs(element.scrollLeft - target.current) > 2) return;
      target.current = null;
    }
    const next = Math.max(0, Math.min(maxIndex, Math.round(element.scrollLeft / STEP)));
    if (next !== start) setIndex(next);
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (event.pointerType === "touch" || event.button !== 0 || !view.current) return;
    // Clic en la barra de desplazamiento de la conversación: no arrastra el carrusel.
    const hit = event.target;
    if (
      hit instanceof HTMLElement &&
      hit.classList.contains("av-conv") &&
      event.nativeEvent.offsetX > hit.clientWidth
    )
      return;
    drag.current = {
      x: event.clientX,
      y: event.clientY,
      left: view.current.scrollLeft,
      id: event.pointerId,
      on: false,
    };
  }
  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    const state = drag.current;
    const element = view.current;
    if (!state || !element || event.pointerId !== state.id) return;
    const dx = (event.clientX - state.x) / (scale || 1);
    const dy = (event.clientY - state.y) / (scale || 1);
    // Gesto vertical: es de la conversación; el carrusel no se arrastra.
    if (!state.on && Math.abs(dy) > DRAG_START && Math.abs(dy) >= Math.abs(dx)) {
      drag.current = null;
      return;
    }
    if (!state.on && Math.abs(dx) > DRAG_START) {
      state.on = true;
      target.current = null;
      element.classList.add("drag");
      element.setPointerCapture?.(event.pointerId);
    }
    if (state.on) element.scrollLeft = state.left - dx;
  }
  function endDrag(event: PointerEvent<HTMLDivElement>) {
    const state = drag.current;
    const element = view.current;
    if (!state || !element || event.pointerId !== state.id) return;
    drag.current = null;
    if (!state.on) return;
    element.classList.remove("drag");
    const dx = (event.clientX - state.x) / (scale || 1);
    suppressClick.current = true;
    setTimeout(() => {
      suppressClick.current = false;
    }, 0);
    // Un arrastre corto basta para pasar al siguiente chat.
    const bias = dx < -40 ? 0.35 : dx > 40 ? -0.35 : 0;
    const next = Math.max(0, Math.min(maxIndex, Math.round(element.scrollLeft / STEP + bias)));
    setIndex(next);
    element.scrollLeft = next * STEP;
  }

  const byId = new Map(items.map((item) => [item.id, item]));
  const shown = new Set(visible);
  const position = new Map(ids.map((id, n) => [id, n + 1]));
  return (
    <section className="av-carea" aria-label="Chats en vivo">
      <div className="av-cwin">
        {win.pins.length > 0 && (
          <div className="av-cpinned">{win.pins.map((id) => renderChat(id, true))}</div>
        )}
        <div
          className="av-cview"
          ref={view}
          onScroll={onScroll}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onClickCapture={(event) => {
            if (!suppressClick.current) return;
            event.preventDefault();
            event.stopPropagation();
          }}
        >
          {free.length === 0 && items.length === 0 ? (
            <p className="av-cempty">Esperando atacantes…</p>
          ) : (
            free.map((id) => renderChat(id, shown.has(id)))
          )}
        </div>
      </div>
      <nav className="av-cnav" ref={nav} aria-label="Navegar entre chats">
        <button
          type="button"
          className="av-cnav-btn"
          aria-label="Chat anterior"
          disabled={start <= 0}
          onClick={() => goTo.current(start - 1)}
        >
          <svg
            width="26"
            height="26"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M15 5l-7 7 7 7" />
          </svg>
        </button>
        <div className="av-cdots">
          {order.map((id) => {
            const item = byId.get(id);
            if (!item) return null;
            const isPinned = pinned.includes(id);
            const inView = shown.has(id);
            const classes = [
              "av-ci",
              `st-${item.tone}`,
              inView ? "in" : "",
              isPinned ? "pinned" : "",
              pulses.has(id) ? "evt" : "",
            ];
            return (
              <button
                key={id}
                type="button"
                className={classes.filter(Boolean).join(" ")}
                aria-label={`Ir al chat ${position.get(id)}: ${item.label}`}
                aria-current={inView ? "true" : undefined}
                title={item.title}
                data-tone={item.tone}
                onClick={() => {
                  if (!isPinned) goTo.current(focusIndex(free, id, start, slots));
                }}
              >
                <i aria-hidden="true" />
                <span className="ca">{item.short}</span>
                <PinIcon size={16} className="pg" />
              </button>
            );
          })}
          {frames(order, visible).map((frame, n) => (
            <div
              // biome-ignore lint/suspicious/noArrayIndexKey: un marco por tramo visible.
              key={n}
              className="av-cframe"
              aria-hidden="true"
              style={{ left: frame.left, width: frame.width }}
            />
          ))}
        </div>
        <button
          type="button"
          className="av-cnav-btn"
          aria-label="Chat siguiente"
          disabled={start >= maxIndex}
          onClick={() => goTo.current(start + 1)}
        >
          <svg
            width="26"
            height="26"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </nav>
    </section>
  );
}
