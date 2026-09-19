import type { ApiError } from "@/lib/api/types";
import { getIdToken } from "@/lib/auth/cognito";
import { getSession } from "@/lib/auth/session";
import { isDemoMode } from "@/lib/app/mode";
import type {
  ActivateResponse,
  Adherence,
  AudioClip,
  BoxCheckItem,
  Circle,
  DocumentUploads,
  Invite,
  JoinResponse,
  Language,
  Plan,
  PushSubscriptionJSON,
} from "@/lib/api/types";

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

type RequestOptions = RequestInit & {
  auth?: boolean;
  timeoutMs?: number;
};

async function bearer(): Promise<string | null> {
  const session = getSession();
  if (session?.role === "caregiver" && session.caregiverToken) {
    return session.caregiverToken;
  }
  const idToken = await getIdToken();
  if (idToken) return idToken;
  return session?.caregiverToken ?? null;
}

function ownerCircleId(): string | null {
  const session = getSession();
  if (session?.role === "caregiver") return session.circleId;
  return session?.circleId ?? null;
}

export function withCircleQuery(path: string, circleId?: string | null): string {
  const id = circleId ?? ownerCircleId();
  if (!id) return path;
  const join = path.includes("?") ? "&" : "?";
  return `${path}${join}circleId=${encodeURIComponent(id)}`;
}

async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
  if (!API_BASE) {
    throw new ApiRequestError({
      code: "auth_unavailable",
      message: "API base URL is not configured.",
    });
  }

  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (init.auth !== false) {
    const token = await bearer();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const timeoutMs = init.timeoutMs;
  const controller = timeoutMs ? new AbortController() : null;
  const timer = timeoutMs ? window.setTimeout(() => controller?.abort(), timeoutMs) : null;

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      signal: init.signal ?? controller?.signal,
    });
    if (response.status === 204) {
      return undefined as T;
    }

    const payload = (await response.json().catch(() => null)) as T | ApiError | null;
    if (!response.ok) {
      const error = payload as ApiError | null;
      let code = error?.code;
      if (!code) {
        if (response.status === 401) code = "unauthorized";
        else if (response.status === 404) code = "not_found";
        else code = "retryable";
      }
      throw new ApiRequestError({
        code,
        message: error?.message ?? `Request failed for ${path}`,
        details: error?.details,
      });
    }
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("aftercare:api-success"));
    }
    return payload as T;
  } finally {
    if (timer) window.clearTimeout(timer);
  }
}

export async function putPresigned(uploadUrl: string, file: Blob, contentType: string): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: { "Content-Type": contentType },
    body: file,
  });
  if (!response.ok) {
    throw new ApiRequestError({
      code: "validation_failed",
      message: "The photo upload did not complete. Photograph the page again.",
    });
  }
}

export const api = {
  health: () => request<{ ok: boolean; commit?: string }>("/health", { auth: false }),
  createCircle: (body: { name: string; language: Language }) =>
    request<{ circleId: string }>("/circles", { method: "POST", body: JSON.stringify(body) }),
  getCircle: (circleId: string) => request<Circle>(`/circles/${circleId}`),
  invite: (circleId: string) =>
    request<Invite>(`/circles/${circleId}/invite`, { method: "POST" }),
  joinCircle: (circleId: string, token: string) =>
    request<JoinResponse>(`/circles/${circleId}/join`, {
      method: "POST",
      body: JSON.stringify({ token }),
      auth: false,
    }),
  registerPush: (circleId: string, subscription: PushSubscriptionJSON) =>
    request<void>(`/circles/${circleId}/push`, {
      method: "POST",
      body: JSON.stringify({ subscription }),
    }),
  createDocument: (body: { circleId: string; pageCount: number; contentType: string }) =>
    request<DocumentUploads>("/documents", { method: "POST", body: JSON.stringify(body) }),
  extract: (documentId: string, circleId: string) =>
    request<Plan>(`/documents/${documentId}/extract`, {
      method: "POST",
      body: JSON.stringify({ circleId }),
      timeoutMs: 130_000,
    }),
  getPlan: (planId: string, circleId?: string | null) =>
    request<Plan>(withCircleQuery(`/plans/${planId}`, circleId)),
  patchPlan: (
    planId: string,
    body: { circleId: string; medicines: Plan["medicines"]; userEdited: boolean; language?: Language; slotTimes?: Plan["slotTimes"] },
  ) => request<Plan>(`/plans/${planId}`, { method: "PATCH", body: JSON.stringify(body) }),
  activatePlan: (planId: string, circleId: string) =>
    request<ActivateResponse>(`/plans/${planId}/activate`, {
      method: "POST",
      body: JSON.stringify({ circleId }),
    }),
  adherence: (planId: string, days: number, circleId?: string | null) =>
    request<Adherence>(withCircleQuery(`/plans/${planId}/adherence?days=${days}`, circleId)),
  audio: (planId: string, lang: Language, circleId?: string | null) =>
    request<AudioClip>(withCircleQuery(`/plans/${planId}/audio?lang=${lang}`, circleId)),
  markGiven: (doseId: string) =>
    request(`/doses/${encodeURIComponent(doseId)}/given`, { method: "POST" }),
  boxCheck: (body: { circleId: string; planId: string; documentId: string }) =>
    request<{ items: BoxCheckItem[] }>("/boxcheck", {
      method: "POST",
      body: JSON.stringify(body),
      timeoutMs: 60_000,
    }),
};

export function isDemoOnly(): boolean {
  return isDemoMode();
}
