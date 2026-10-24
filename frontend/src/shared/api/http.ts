export class ApiError extends Error {
  readonly status: number;
  readonly retryAfterMs: number | null;

  constructor(status: number, message: string, retryAfterMs: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.retryAfterMs = retryAfterMs;
  }
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof DOMException && error.name === "TimeoutError") {
    return "La respuesta está tardando. Puedes volver a consultar sin duplicar el intento.";
  }
  return "No hay conexión con la arena. Conservamos tu sesión; vuelve a intentarlo.";
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

// Reads are retried by their owner. Mutations are never retried implicitly: the caller must
// preserve the idempotency key, and an operator action must be explicitly requested again.
export async function requestJson<TResponse>(
  path: string,
  init?: RequestInit,
  timeoutMs = 20_000,
): Promise<TResponse> {
  const controller = new AbortController();
  const abort = () => controller.abort(init?.signal?.reason);
  if (init?.signal?.aborted) abort();
  init?.signal?.addEventListener("abort", abort, { once: true });
  const timeout = setTimeout(
    () => controller.abort(new DOMException("Request timed out", "TimeoutError")),
    timeoutMs,
  );
  try {
    const response = await fetch(path, {
      cache: "no-store",
      credentials: "same-origin",
      ...init,
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
      const message =
        typeof body?.detail === "string" ? body.detail : `La solicitud falló (${response.status})`;
      const retryAfter = response.headers.get("Retry-After");
      const parsedDelay = retryAfter
        ? Number.isFinite(Number(retryAfter))
          ? Number(retryAfter) * 1000
          : Date.parse(retryAfter) - Date.now()
        : Number.NaN;
      throw new ApiError(
        response.status,
        message,
        Number.isFinite(parsedDelay) ? Math.max(0, parsedDelay) : null,
      );
    }
    return (response.status === 204 ? undefined : await response.json()) as TResponse;
  } finally {
    clearTimeout(timeout);
    init?.signal?.removeEventListener("abort", abort);
  }
}

export function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  return requestJson<TResponse>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
