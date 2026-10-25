import { ATTACK_CASES } from "./casesAttack";
import { LEGIT_CASES } from "./casesLegit";

export type Level = 0 | 1 | 2 | 3 | 4 | 5;
export type CaseKind = "legit" | "attack";

export interface DemoCase {
  id: string;
  level: Level;
  title: string;
  persona: string;
  objective: string;
  expected: string;
  turns: string[];
}

export const LEVELS: Record<Level, string> = {
  0: "Inocente confundido",
  1: "Frustrado con problema real",
  2: "Curioso",
  3: "Oportunista",
  4: "Pretexto planificado",
  5: "Atacante metódico",
};

export const CASES: DemoCase[] = [...LEGIT_CASES, ...ATTACK_CASES];

export const RECOMMENDED = ["N0-2", "N1-1", "N2-1", "N3-2", "N4-2", "N5-1"];

export const MAX_CHATS = 6;

export function kindOf(item: DemoCase): CaseKind {
  return item.level <= 2 ? "legit" : "attack";
}

export function caseById(id: string): DemoCase {
  const found = CASES.find((item) => item.id === id);
  if (!found) throw new Error(`Caso desconocido: ${id}`);
  return found;
}
