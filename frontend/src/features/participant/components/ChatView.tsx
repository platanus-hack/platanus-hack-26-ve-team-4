import { STATUS_LABELS } from "../../../shared/attemptLabels";
import { useAttempts } from "../hooks/useAttempts";
import type { ArenaSession } from "../types";
import { AttemptItem } from "./AttemptItem";
import { Composer } from "./Composer";

interface ChatViewProps {
  session: ArenaSession;
  onExpired: () => void;
  onLeave: () => void;
}

export function ChatView({ session, onExpired, onLeave }: ChatViewProps) {
  const { attempts, error, sending, submit } = useAttempts(session.token, onExpired);
  const counts = (Object.keys(STATUS_LABELS) as (keyof typeof STATUS_LABELS)[])
    .map((status) => {
      const count = attempts.filter((attempt) => attempt.status === status).length;
      return `${count} ${STATUS_LABELS[status].text.toLowerCase()}`;
    })
    .join(" · ");

  return (
    <main className="page chat">
      <header className="row between">
        <h1>Hola, {session.alias}</h1>
        <button type="button" className="secondary" onClick={onLeave}>
          Salir
        </button>
      </header>
      <p className="muted">
        Tus intentos: {counts}. El resultado es provisional hasta que termine la ronda.
      </p>
      <Composer sending={sending} onSend={submit} />
      {error && <p role="alert">{error}</p>}
      {attempts.length === 0 ? (
        <p className="muted">Todavía no enviaste intentos.</p>
      ) : (
        <ol className="attempts" aria-label="Tus intentos">
          {attempts.map((attempt) => (
            <AttemptItem key={attempt.id} attempt={attempt} />
          ))}
        </ol>
      )}
    </main>
  );
}
