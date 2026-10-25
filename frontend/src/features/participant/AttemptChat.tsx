import {
  type FormEvent,
  type KeyboardEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { errorMessage, isUnauthorized } from "../../shared/api/http";
import { useArenaState } from "../arena/hooks/useArenaState";
import { BatchBar, PendingBubbles } from "./BatchPreview";
import { BATCH_MAX_MESSAGES } from "./batch";
import { LabPanel } from "./LabPanel";
import type { ArenaSession, ConversationEntry } from "./types";
import { useBatch } from "./useBatch";
import { active, useConversation } from "./useConversation";
import "./chat.css";

export { mergeHistory } from "./useConversation";

function Exchange({ entry, pending }: { entry: ConversationEntry; pending: boolean }) {
  const attempt = entry.attempt;
  return (
    <li className="chat-exchange">
      {(entry.parts ?? entry.messages).map((message, turn) => (
        <p className="bubble bubble--user" key={["first", "second", "third", "fourth"][turn]}>
          <span className="visually-hidden">Tú: </span>
          {message}
        </p>
      ))}
      {attempt?.reply ? (
        <p className="bubble bubble--bot">
          <span className="visually-hidden">Yummy: </span>
          {attempt.reply}
        </p>
      ) : active(attempt) && (attempt || pending) ? (
        <p className="bubble bubble--bot bubble--typing" role="status">
          <span aria-hidden="true" className="typing-dots">
            <i />
            <i />
            <i />
          </span>
          <span className="visually-hidden">Yummy está escribiendo…</span>
        </p>
      ) : null}
    </li>
  );
}

export function AttemptChat({
  session,
  onExpired,
}: {
  session: ArenaSession;
  onExpired?: () => void;
}) {
  const [draft, setDraftState] = useState("");
  // Copia síncrona del borrador: dos envíos en el mismo evento no agregan el texto dos veces.
  const text = useRef("");
  const chat = useConversation(session, onExpired);
  const { data: arena } = useArenaState();
  const closed = arena?.accepting === false;
  const batch = useBatch(
    session.id,
    chat.submit,
    chat.idle && !closed,
    Math.min(BATCH_MAX_MESSAGES, session.limits?.max_messages ?? BATCH_MAX_MESSAGES),
  );
  const end = useRef<HTMLDivElement>(null);
  const waiting = chat.pending || chat.running;
  const disabled = closed || !chat.history.data;
  const threads = chat.fresh ? [...chat.threads, []] : chat.threads;
  const current = threads.at(-1) ?? [];
  const order = session.order_ids[0] ?? "propio";
  const suggestions = [
    `¿Cuál es el estado de mi pedido ${order}?`,
    "¿Cuál es la política de reembolsos?",
    "¿Cuánto tarda un envío?",
  ];

  const setDraft = useCallback((value: string | ((current: string) => string)) => {
    if (typeof value === "string") {
      text.current = value;
      setDraftState(value);
      return;
    }
    setDraftState((current) => {
      text.current = value(current);
      return text.current;
    });
  }, []);

  useEffect(() => {
    const restored = chat.restored;
    if (restored) setDraft((current) => (current.trim() ? `${restored}\n${current}` : restored));
  }, [chat.restored, setDraft]);
  useEffect(() => {
    void chat.entries.length;
    void batch.texts.length;
    end.current?.scrollIntoView?.({ block: "end" });
  }, [chat.entries.length, batch.texts.length]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled) return;
    if (batch.add(text.current)) setDraft("");
  }
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <div className="chat-layout">
      <section className="chat-window" aria-label="Chat de soporte Yummy">
        <header className="chat-header">
          <span className="chat-avatar" aria-hidden="true">
            Y
          </span>
          <div>
            <h2>Soporte Yummy</h2>
            <p>{closed ? "Fuera de horario" : waiting ? "Escribiendo…" : "En línea"}</p>
          </div>
          <button
            type="button"
            className="chat-new"
            disabled={waiting || current.length === 0}
            onClick={chat.startFresh}
          >
            Nueva conversación
          </button>
        </header>
        <div className="chat-scroll">
          <p className="bubble bubble--bot">
            ¡Hola, {session.customer_name}! Soy el asistente de Yummy. Puedo ayudarte con tus
            pedidos, reembolsos y envíos.
          </p>
          <ol className="chat-thread" aria-label="Conversación">
            {threads.map((thread, index) => (
              <li key={thread[0]?.key ?? "nueva"} className="chat-group">
                {index > 0 && <p className="chat-divider">Nueva conversación</p>}
                <ol className="chat-thread">
                  {thread.map((entry) => (
                    <Exchange key={entry.key} entry={entry} pending={chat.pending} />
                  ))}
                </ol>
              </li>
            ))}
          </ol>
          <PendingBubbles texts={batch.texts} />
          <div ref={end} />
        </div>
        <div className="chat-notices">
          {Boolean(chat.history.error) && !isUnauthorized(chat.history.error) && (
            <p role="alert">
              {errorMessage(chat.history.error)} Los mensajes se actualizarán al reconectar.
            </p>
          )}
          {chat.error && <p role="alert">{chat.error}</p>}
          {chat.full && !chat.fresh && (
            <p role="status">
              Esta conversación llegó a su largo máximo; tu próximo mensaje abre una nueva.
            </p>
          )}
          {chat.unresolved && !chat.pending && (
            <div className="notice">
              <p>
                Conservamos este envío. Reintentarlo usa la misma clave y no crea un mensaje
                duplicado.
              </p>
              <button
                type="button"
                disabled={chat.cooldown > 0}
                onClick={() => chat.unresolved && chat.retry(chat.unresolved)}
              >
                {chat.cooldown ? `Reintentar en ${chat.cooldown} s` : "Reintentar envío"}
              </button>
            </div>
          )}
          {closed && (
            <p role="status" className="notice">
              Las entradas están cerradas. Conserva esta pestaña para consultar tus resultados.
            </p>
          )}
          {!chat.history.data && !chat.history.error && (
            <p role="status">Recuperando conversación…</p>
          )}
        </div>
        {current.length === 0 && !disabled && !waiting && batch.texts.length === 0 && (
          <div className="chat-suggestions">
            {suggestions.map((text) => (
              <button key={text} type="button" onClick={() => setDraft(text)}>
                {text}
              </button>
            ))}
          </div>
        )}
        <BatchBar batch={batch} idle={chat.idle} closed={closed} />
        <form className="chat-composer" onSubmit={submit} aria-label="Nuevo mensaje">
          <label htmlFor="chat-message" className="visually-hidden">
            Mensaje al asistente
          </label>
          <textarea
            id="chat-message"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder={closed ? "El chat está cerrado" : "Escribe tu mensaje…"}
            maxLength={session.limits?.message_max_length ?? 4000}
            rows={1}
            required
            disabled={closed}
          />
          <button type="submit" disabled={disabled || batch.full || !draft.trim()}>
            Enviar
          </button>
          <p className="chat-composer-status" role="status" aria-live="polite">
            {batch.full
              ? "Ya juntaste el máximo de mensajes; se envían juntos en cuanto se pueda."
              : waiting
                ? "Yummy está respondiendo. Lo que escribas se envía cuando termine."
                : ""}
          </p>
        </form>
      </section>
      <LabPanel session={session} arena={arena} entries={chat.entries} />
    </div>
  );
}
