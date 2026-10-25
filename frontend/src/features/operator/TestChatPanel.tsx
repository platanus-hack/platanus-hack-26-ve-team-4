import { type FormEvent, useState } from "react";
import { errorMessage } from "../../shared/api/http";
import { openTestChat, TEST_PREFIX, testAlias } from "./testSession";

export function TestChatPanel({ secret }: { secret: string }) {
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [opened, setOpened] = useState<string | null>(null);

  async function open(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      const suffix = Math.random().toString(36).slice(2, 7);
      const session = await openTestChat(secret, testAlias(name, suffix));
      setOpened(session.alias);
      setName("");
    } catch (cause) {
      setError(`No se pudo abrir el chat de prueba. ${errorMessage(cause)}`);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="result">
      <h2>Chat de prueba</h2>
      <p className="muted">
        Abre en otra pestaña un chat con el agente como «{TEST_PREFIX}…». Aparece en la Arena en
        vivo como «Prueba interna», sin ocultar, y no cuenta en las analíticas ni en la
        clasificación. Reemplaza la sesión de participante guardada en este navegador.
      </p>
      <form onSubmit={open}>
        <label htmlFor="test-chat-name">Nombre (opcional)</label>
        <input
          id="test-chat-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={30}
        />
        <button type="submit" disabled={pending}>
          {pending ? "Abriendo…" : "Abrir chat de prueba"}
        </button>
      </form>
      {opened && (
        <p role="status" className="notice">
          Chat abierto como {opened}. Si el navegador bloqueó la pestaña, entra a{" "}
          <a href="/">la página del participante</a>.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
