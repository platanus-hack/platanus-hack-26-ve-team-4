import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../../shared/api/http";
import { getMe } from "../api/attempts";
import type { ArenaSession } from "../types";

const STORAGE_KEY = "agent-zero.session";

function read(): ArenaSession | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ArenaSession) : null;
  } catch {
    return null;
  }
}

function write(session: ArenaSession | null) {
  try {
    if (session) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // Sin almacenamiento (modo privado): la sesión vive solo mientras la pestaña siga abierta.
  }
}

/** La sesión sobrevive a una recarga de la pestaña; el servidor confirma que sigue vigente. */
export function useStoredSession() {
  const [session, setSession] = useState<ArenaSession | null>(read);
  const [expired, setExpired] = useState(false);

  const save = useCallback((next: ArenaSession | null) => {
    write(next);
    setSession(next);
  }, []);

  const expire = useCallback(() => {
    save(null);
    setExpired(true);
  }, [save]);

  useEffect(() => {
    const stored = read();
    if (!stored) {
      return;
    }
    getMe(stored.token).catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 401) {
        expire();
      }
    });
  }, [expire]);

  return { session, save, expire, expired };
}
