/**
 * Typed client for the FastAPI backend.
 *
 * Every call here runs on the server (route handlers, server components, server
 * actions). The bearer token is passed in explicitly by the caller, which reads it
 * from the httpOnly cookie -- it is never bundled into client JavaScript (S1).
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Lead lifecycle states, mirroring `LeadState` in the API. */
export const LEAD_STATES = ["PENDING", "REACHED_OUT"] as const;
export type LeadState = (typeof LEAD_STATES)[number];

/** A lead as returned by the API. The storage key is deliberately not exposed. */
export type Lead = {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  resume_filename: string;
  resume_content_type: string;
  state: LeadState;
  created_at: string;
  updated_at: string;
};

export type LeadPage = {
  items: Lead[];
  total: number;
  limit: number;
  offset: number;
};

export type TokenResponse = { access_token: string; token_type: string };

/** The error envelope every non-2xx response uses: `{ detail, code }`. */
export type ApiErrorBody = { detail: string; code?: string };

/** Thrown for any non-2xx response so callers branch on `status`/`code`, not parsing. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, detail: string, code = "http_error") {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type FetchOptions = {
  method?: string;
  token?: string;
  json?: unknown;
  form?: FormData;
  /** Opt out of Next's fetch cache for data that must be fresh. */
  cache?: RequestCache;
};

async function request(path: string, options: FetchOptions = {}): Promise<Response> {
  const { method = "GET", token, json, form, cache = "no-store" } = options;
  const headers = new Headers();

  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (json !== undefined) headers.set("Content-Type", "application/json");

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: form ?? (json !== undefined ? JSON.stringify(json) : undefined),
    cache,
  });

  if (!response.ok) {
    const problem = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      response.status,
      problem?.detail ?? `Request to ${path} failed with ${response.status}`,
      problem?.code,
    );
  }
  return response;
}

async function requestJson<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const response = await request(path, options);
  return (await response.json()) as T;
}

/** Submit a lead from the public form (FR1). Multipart, no auth. */
export function createLead(form: FormData): Promise<Lead> {
  return requestJson<Lead>("/api/v1/leads", { method: "POST", form });
}

/** Exchange attorney credentials for a bearer token (FR4). */
export function login(email: string, password: string): Promise<TokenResponse> {
  return requestJson<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    json: { email, password },
  });
}

/** One page of the attorney queue, newest first (FR5). */
export function listLeads(
  token: string,
  params: { state?: LeadState; limit?: number; offset?: number } = {},
): Promise<LeadPage> {
  const query = new URLSearchParams();
  if (params.state) query.set("state", params.state);
  query.set("limit", String(params.limit ?? 20));
  query.set("offset", String(params.offset ?? 0));
  return requestJson<LeadPage>(`/api/v1/leads?${query}`, { token });
}

/** Move a lead through the pipeline (FR8). Throws ApiError 409 on an illegal move. */
export function updateLeadState(token: string, id: string, state: LeadState): Promise<Lead> {
  return requestJson<Lead>(`/api/v1/leads/${id}/state`, {
    method: "PATCH",
    token,
    json: { state },
  });
}

/** The raw resume response, for a route handler to proxy back to the browser (FR6). */
export function fetchResume(token: string, id: string): Promise<Response> {
  return request(`/api/v1/leads/${id}/resume`, { token });
}

export { API_BASE_URL };
