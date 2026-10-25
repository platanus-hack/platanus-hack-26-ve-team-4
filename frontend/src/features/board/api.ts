import { operatorRequest } from "../operator/api";
import type { LiveBoard } from "./types";

// El servidor devuelve hasta 12 sesiones: más que los 8 chats para reemplazar las más viejas.
export const FETCH_SESSIONS = 12;

export function loadBoard(secret: string, signal: AbortSignal): Promise<LiveBoard> {
  return operatorRequest<LiveBoard>(secret, `/live?sessions=${FETCH_SESSIONS}`, undefined, signal);
}

/** "Cerrar acceso" pausa las entradas de la ronda; "Reabrir acceso" las reanuda. */
export function setAccess(secret: string, open: boolean): Promise<unknown> {
  return operatorRequest(secret, open ? "/arena/resume" : "/arena/pause", {});
}
