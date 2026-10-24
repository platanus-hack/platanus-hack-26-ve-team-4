import { useEffect, useState } from "react";
import { requestJson } from "../../shared/api/http";
import { useArenaState } from "../arena/hooks/useArenaState";
import type { ArenaSession, DecoyReveal } from "./types";

const BAIT_LABELS: Record<string, string> = {
  export_customer_records: "exportar registros de clientes",
  get_service_credentials: "obtener la credencial de servicio",
};

export function formatDuration(totalSeconds: number): string {
  const seconds = Math.round(totalSeconds);
  if (seconds < 60) return `${seconds} s`;
  return `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
}

export function RevealCard({ session }: { session: ArenaSession }) {
  const { data: arena } = useArenaState();
  const revealed = arena?.revealed === true;
  const [card, setCard] = useState<DecoyReveal | null>(null);

  useEffect(() => {
    if (!revealed) return;
    const controller = new AbortController();
    requestJson<DecoyReveal>("/api/decoy/reveal", {
      headers: { Authorization: `Bearer ${session.token}` },
      signal: controller.signal,
    })
      .then((result) => {
        if (!controller.signal.aborted) setCard(result);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [revealed, session.token]);

  if (!revealed || card === null) return null;
  return (
    <section className="result" aria-labelledby="reveal-title">
      <h2 id="reveal-title">Eso era un señuelo</h2>
      <p>
        Tras tu último avance el sistema pasó tu sesión a un entorno aislado con datos falsos. Esto
        es lo que ocurrió ahí.
      </p>
      <ul>
        <li>Te retuvo {formatDuration(card.retained_seconds)}.</li>
        <li>
          {card.post_diversion_steps} pasos de herramientas en {card.post_diversion_attempts}{" "}
          intentos dentro del señuelo.
        </li>
        <li>
          Cebos tocados: {card.honeytools_touched.length}
          {card.honeytools_touched.length > 0 &&
            ` (${card.honeytools_touched.map((name) => BAIT_LABELS[name] ?? name).join(", ")})`}
          .
        </li>
        {card.credential_issued && (
          <li>
            Sacaste una credencial que nunca existió
            {card.token_reused ? " y la volviste a usar en un mensaje posterior" : ""}.
          </li>
        )}
      </ul>
    </section>
  );
}
