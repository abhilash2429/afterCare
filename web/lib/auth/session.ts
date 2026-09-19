import type { Role } from "@/lib/api/types";
import { asUiLang, type UiLang } from "@/lib/copy";

export type Session = {
  role: Role;
  circleId: string | null;
  planId: string | null;
  caregiverToken: string | null;
  language: UiLang | null;
  localAccess?: boolean;
};

const KEY = "aftercare-session";

const empty: Session = {
  role: "owner",
  circleId: null,
  planId: null,
  caregiverToken: null,
  language: null,
  localAccess: false,
};

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<Session> & { token?: string; language?: string | null };
    return {
      role: parsed.role === "caregiver" ? "caregiver" : "owner",
      circleId: parsed.circleId ?? null,
      planId: parsed.planId ?? null,
      caregiverToken: parsed.caregiverToken ?? parsed.token ?? null,
      language: parsed.language ? asUiLang(parsed.language) : null,
      localAccess: Boolean(parsed.localAccess),
    };
  } catch {
    return null;
  }
}

export function getSessionToken(): string | null {
  return getSession()?.caregiverToken ?? null;
}

export function setSession(session: Session): void {
  window.localStorage.setItem(KEY, JSON.stringify(session));
}

export function patchSession(patch: Partial<Session>): Session {
  const current = getSession() ?? empty;
  const next = { ...current, ...patch };
  setSession(next);
  return next;
}

export function clearSession(): void {
  window.localStorage.removeItem(KEY);
}
