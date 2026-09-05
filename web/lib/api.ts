/**
 * Typed fetch wrapper for the FastAPI backend.
 *
 * Stage 0: transport only -- no endpoints are modelled yet. Server components pass a
 * bearer token explicitly (P0); the token is never read from client-side JS (S1).
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Error envelope the API returns for every failure: `{ detail, code }` (M6). */
export type ApiErrorBody = {
  detail: string;
  code?: string;
};

/** Thrown for any non-2xx response so callers branch on status, not on parsing. */
export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(status: number, detail: string, code?: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export type ApiFetchOptions = Omit<RequestInit, "body"> & {
  /** Bearer token, forwarded server-side only. */
  token?: string;
  /** JSON-serialisable body, or a FormData for multipart uploads. */
  body?: unknown;
};

/**
 * Call `path` (e.g. `/api/v1/health`) on the API and parse the JSON response.
 *
 * @throws {ApiError} when the response status is not 2xx.
 */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { token, body, headers, ...rest } = options;

  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  const requestHeaders = new Headers(headers);

  if (token) {
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }
  if (body !== undefined && !isFormData) {
    requestHeaders.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: requestHeaders,
    body: isFormData ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const fallback = `Request to ${path} failed with ${response.status}`;
    const problem = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(response.status, problem?.detail ?? fallback, problem?.code);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export { API_BASE_URL };
