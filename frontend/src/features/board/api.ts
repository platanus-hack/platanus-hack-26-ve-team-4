import { operatorRequest } from "../operator/api";
import type { LiveBoard } from "./types";

export const SLOT_COUNT = 6;
// El servidor devuelve más sesiones que casillas para poder reemplazar las más viejas.
const FETCH_SESSIONS = 12;

export function loadBoard(secret: string, signal: AbortSignal): Promise<LiveBoard> {
  return operatorRequest<LiveBoard>(secret, `/live?sessions=${FETCH_SESSIONS}`, undefined, signal);
}
