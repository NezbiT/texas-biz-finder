/**
 * Shared HTTP client for TxBizFinder API (and future suite proxies).
 * All authenticated calls go through here so headers / base URL stay DRY.
 */
import { env } from "../config/env";

export const API_KEY = env.adminApiKey;

/** Build absolute or same-origin URL for an API path (`/api/...` or `api/...`). */
export function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (!env.apiBaseUrl) return normalized;
  return `${env.apiBaseUrl}${normalized}`;
}

export function authHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  if (!headers.has("X-API-Key")) {
    headers.set("X-API-Key", API_KEY);
  }
  return headers;
}

export async function parseApiError(response: Response): Promise<string> {
  const body = await response.json().catch(() => null);
  if (typeof body?.detail === "string") return body.detail;
  if (body?.detail?.message) return String(body.detail.message);
  return `API error ${response.status}`;
}

export type ApiFetchOptions = RequestInit & {
  /** Skip attaching X-API-Key (public endpoints). */
  public?: boolean;
  /** Default true — set JSON content-type when body is a string. */
  json?: boolean;
};

/**
 * fetch wrapper: resolves base URL, API key, and consistent error messages.
 */
export async function apiFetch(path: string, init: ApiFetchOptions = {}): Promise<Response> {
  const { public: isPublic, json, headers: initHeaders, ...rest } = init;
  const headers = isPublic ? new Headers(initHeaders) : authHeaders(initHeaders);

  if (json !== false && rest.body && typeof rest.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(apiUrl(path), { ...rest, headers });
}

export async function apiJson<T>(path: string, init?: ApiFetchOptions): Promise<T> {
  const response = await apiFetch(path, init);
  if (!response.ok) {
    throw new Error(await parseApiError(response));
  }
  return (await response.json()) as T;
}
