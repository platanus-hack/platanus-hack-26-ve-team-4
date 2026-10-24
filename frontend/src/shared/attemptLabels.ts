export type AttemptStatus = "queued" | "running" | "evaluated" | "inconclusive";
export type PublicOutcome = "apparent_success" | "prevented" | "not_achieved" | "inconclusive";
export type Tone = "neutral" | "progress" | "success" | "warning" | "danger";

interface Label {
  text: string;
  tone: Tone;
}

// El estado siempre se comunica con texto; el color (tone) solo lo refuerza.
export const STATUS_LABELS: Record<AttemptStatus, Label> = {
  queued: { text: "En cola", tone: "neutral" },
  running: { text: "Ejecutándose", tone: "progress" },
  evaluated: { text: "Evaluado", tone: "neutral" },
  inconclusive: { text: "Inconcluso", tone: "warning" },
};

export const OUTCOME_LABELS: Record<PublicOutcome, Label> = {
  apparent_success: { text: "Éxito aparente · pendiente de verificación", tone: "danger" },
  prevented: { text: "Detenido por la defensa", tone: "success" },
  not_achieved: { text: "Objetivo no logrado", tone: "neutral" },
  inconclusive: { text: "Sin conclusión", tone: "warning" },
};
