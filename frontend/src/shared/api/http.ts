export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | null;
  readonly retryAfter: number | null;

  constructor(status: number, message: string, detail: string | null, retryAfter: number | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

interface RequestOptions {
  token?: string | null;
}

async function readDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}

async function request<TResponse>(
  path: string,
  init: RequestInit,
  { token }: RequestOptions,
): Promise<TResponse> {
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    const retryAfter = Number(response.headers.get("Retry-After"));
    throw new ApiError(
      response.status,
      `La solicitud a ${path} falló (${response.status})`,
      await readDetail(response),
      Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
    );
  }
  return (await response.json()) as TResponse;
}

export function getJson<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
  return request<TResponse>(path, { method: "GET" }, options);
}

export function postJson<TResponse>(
  path: string,
  body: unknown,
  options: RequestOptions = {},
): Promise<TResponse> {
  return request<TResponse>(
    path,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    options,
  );
}
