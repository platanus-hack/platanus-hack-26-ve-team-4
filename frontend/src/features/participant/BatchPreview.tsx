// Mensajes del lote: se ven igual que los enviados (misma estructura y lado), así no saltan al salir.

export function PendingBubbles({ texts }: { texts: string[] }) {
  if (texts.length === 0) return null;
  return (
    <ol className="chat-thread" aria-label="Mensajes por enviar">
      {texts.map((message, turn) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: la cola solo crece al final y se vacía entera.
        <li key={turn} className="chat-exchange">
          <p className="bubble bubble--user">
            <span className="visually-hidden">Tú: </span>
            {message}
          </p>
        </li>
      ))}
    </ol>
  );
}

export function TypingBubble() {
  return (
    <p className="bubble bubble--bot bubble--typing" role="status">
      <span aria-hidden="true" className="typing-dots">
        <i />
        <i />
        <i />
      </span>
      <span className="visually-hidden">Yummy está escribiendo…</span>
    </p>
  );
}
