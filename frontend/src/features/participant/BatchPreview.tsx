// Mensajes en cola: se ven como enviados mientras Yummy termina la respuesta anterior.

export function PendingBubbles({ texts }: { texts: string[] }) {
  if (texts.length === 0) return null;
  return (
    <ol className="chat-thread" aria-label="Mensajes por enviar">
      {texts.map((message, turn) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: la cola solo crece al final y se vacía entera.
        <li key={turn}>
          <p className="bubble bubble--user">
            <span className="visually-hidden">Tú: </span>
            {message}
          </p>
        </li>
      ))}
    </ol>
  );
}
