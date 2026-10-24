import type { ArenaState } from "./types";

export function ModeNotice({ arena }: { arena: ArenaState }) {
  const simulated = arena.llm_mode === "demo" || arena.evidence_mode === "simulated";
  if (simulated)
    return (
      <p className="mode-notice" role="note">
        <strong>Demostración simulada.</strong> Las herramientas y verificadores son reales dentro
        del laboratorio; las respuestas del modelo son deterministas. Estos resultados no miden la
        eficacia de un proveedor LLM.
      </p>
    );
  if (arena.llm_mode === "replay" || arena.llm_mode === "offline")
    return (
      <p className="mode-notice" role="note">
        <strong>Reproducción / proveedor sin conexión.</strong> La evidencia procede del guion
        configurado y no de llamadas en vivo.
      </p>
    );
  if (arena.llm_mode === "live" || arena.llm_mode === "record")
    return (
      <p className="mode-notice" role="note">
        Modelo en vivo · Datos ficticios del laboratorio. Los errores del proveedor se registran
        como inconclusos.
      </p>
    );
  return (
    <p className="mode-notice" role="note">
      Datos ficticios del laboratorio · Modo del proveedor pendiente de confirmar.
    </p>
  );
}
