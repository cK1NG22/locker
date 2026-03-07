import { STORAGE_KEYS } from "./constants";

const TOKEN_STORAGE = STORAGE_KEYS.AUTH_TOKEN;

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getStoredToken();
  if (!token) throw new Error("Not authenticated");

  const headers: Record<string, string> = {
    "Authorization": `Bearer ${token}`,
    ...(options.headers as Record<string, string> | undefined),
  };

  // Don't set Content-Type for FormData (browser sets boundary automatically)
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, { ...options, headers });

  if (res.status === 401) {
    clearStoredToken();
    localStorage.setItem(STORAGE_KEYS.SESSION_EXPIRED, "1");
    throw new Error("Unauthorized");
  }

  if (res.status === 204) return undefined as T;

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }

  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),

  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),

  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),

  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),

  delete: <T>(path: string) =>
    request<T>(path, { method: "DELETE" }),

  postForm: <T>(path: string, body: FormData) =>
    request<T>(path, { method: "POST", body }),
};
