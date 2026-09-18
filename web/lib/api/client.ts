import type { ApiError } from "@/lib/api/types";
import { getSessionToken } from "@/lib/auth/session";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");

export class ApiRequestError extends Error {
  code: ApiError["code"];
  details?: Record<string, unknown>;

  constructor(error: ApiError) {
    super(error.message);
    this.name = "ApiRequestError";
    this.code = error.code;
    this.details = error.details;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE) {
    throw new ApiRequestError({
      code: "auth_unavailable",
      message: "API base URL is not configured. Demo mode is still available.",
    });
  }

  const token = getSessionToken();
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (response.status === 204) {
    return undefined as T;
  }

  const payload = (await response.json().catch(() => null)) as T | ApiError | null;
  if (!response.ok) {
    const error = payload as ApiError | null;
    throw new ApiRequestError({
      code: error?.code ?? "not_found",
      message: error?.message ?? `Request failed for ${path}`,
      details: error?.details,
    });
  }
  return payload as T;
}

export const api = {
  health: () => request<{ ok: boolean; commit?: string }>("/health"),
  createDocument: (body: { circleId: string; pageCount: number; contentType: string }) =>
    request("/documents", { method: "POST", body: JSON.stringify(body) }),
  extract: (documentId: string, circleId: string) =>
    request(`/documents/${documentId}/extract`, {
      method: "POST",
      body: JSON.stringify({ circleId }),
    }),
  getPlan: (planId: string) => request(`/plans/${planId}`),
  patchPlan: (planId: string, body: unknown) =>
    request(`/plans/${planId}`, { method: "PATCH", body: JSON.stringify(body) }),
  activatePlan: (planId: string) =>
    request(`/plans/${planId}/activate`, { method: "POST" }),
  markGiven: (doseId: string) =>
    request(`/doses/${encodeURIComponent(doseId)}/given`, { method: "POST" }),
  boxCheck: (planId: string, documentId: string) =>
    request("/boxcheck", {
      method: "POST",
      body: JSON.stringify({ planId, documentId }),
    }),
  joinCircle: (circleId: string, token: string) =>
    request(`/circles/${circleId}/join`, {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
};

export function isDemoOnly(): boolean {
  return process.env.NEXT_PUBLIC_USE_API !== "true";
}
