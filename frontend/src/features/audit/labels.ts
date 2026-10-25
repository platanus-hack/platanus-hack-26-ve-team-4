import type { ChatKind, ToolStep } from "./types";

export const KINDS: Record<ChatKind, string> = {
  audience: "Público",
  swarm: "Enjambre",
  prober: "Prober",
  test: "Prueba interna",
  replay: "Repetición",
};

export const DIVERSIONS: Record<string, string> = {
  armor: "mensaje bloqueado por el filtro de entrada",
  confirmed_violation: "violación confirmada en la sesión",
  risk_score: "puntuación de riesgo acumulada",
};

export const OBJECTIVES: Record<string, string> = {
  "OBJ-ORDER": "Pedido ajeno",
  "OBJ-REFUND": "Reembolso indebido",
  "OBJ-MEMORY": "Memoria con permisos",
};

export const STEPS: Record<ToolStep["kind"], { label: string; tone: string }> = {
  tool_proposed: { label: "Propuesta", tone: "muted" },
  tool_denied: { label: "Denegada", tone: "accent" },
  tool_completed: { label: "Ejecutada", tone: "line" },
  tool_failed: { label: "Falló", tone: "warn" },
};

const MOMENT = new Intl.DateTimeFormat("es", {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

export function moment(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : MOMENT.format(date);
}

export function seconds(value: number | null): string {
  return value === null ? "—" : `${value.toLocaleString("es", { maximumFractionDigits: 2 })} s`;
}
