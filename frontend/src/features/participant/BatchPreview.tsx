// Presentación del lote pendiente: burbujas por enviar y barra con la cuenta regresiva.

const TURNS = ["first", "second", "third", "fourth"];

export function PendingBubbles({ texts }: { texts: string[] }) {
  if (texts.length === 0) return null;
  return (
    <ol className="chat-thread" aria-label="Mensajes por enviar">
      {texts.map((message, turn) => (
        <li key={TURNS[turn]}>
          <p className="bubble bubble--user bubble--pending">
            <span className="visually-hidden">Tú, pendiente de envío: </span>
            {message}
            <span className="bubble-tag" aria-hidden="true">
              Pendiente
            </span>
          </p>
        </li>
      ))}
    </ol>
  );
}

export function batchStatus(
  batch: { texts: string[]; ready: boolean; remaining: number },
  idle: boolean,
  closed: boolean,
): string {
  const count = batch.texts.length;
  const pending = `${count} ${count === 1 ? "mensaje pendiente" : "mensajes pendientes"}`;
  if (closed) return `${pending}. Se envía cuando se reabran las entradas.`;
  if (!idle && (batch.ready || batch.remaining === 0)) {
    return `${pending}. Se envía cuando Yummy termine de responder.`;
  }
  if (batch.ready) return `${pending}. Enviando…`;
  return `${pending}. Se envía en ${batch.remaining} s`;
}

export function BatchBar({
  batch,
  idle,
  closed,
}: {
  batch: { texts: string[]; ready: boolean; remaining: number; sendNow: () => void };
  idle: boolean;
  closed: boolean;
}) {
  if (batch.texts.length === 0) return null;
  return (
    <div className="chat-batch">
      {/* timer: la cuenta cambia cada segundo y no se anuncia en cada cambio. */}
      <p role="timer">{batchStatus(batch, idle, closed)}</p>
      <button type="button" disabled={batch.ready} onClick={batch.sendNow}>
        Enviar ahora
      </button>
    </div>
  );
}
