import type { Role } from "@/lib/api/types";
import { asUiLang, type UiLang } from "@/lib/copy";

export type Session = {
  role: Role;
  circleId: string | null;
  planId: string | null;
  caregiverToken: string | null;
  language: UiLang | null;
};

const KEY = "aftercare-session";

const empty: Session = {
  role: "owner",
  circleId: null,
  planId: null,
  caregiverToken: null,
  language: null,
};

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<Session> & {
      token?: string;
      language?: string | null;
      localAccess?: boolean;
    };
    const session: Session = {
      role: parsed.role === "caregiver" ? "caregiver" : "owner",
      circleId: parsed.circleId ?? null,
      planId: parsed.planId ?? null,
      caregiverToken: parsed.caregiverToken ?? parsed.token ?? null,
      language: parsed.language ? asUiLang(parsed.language) : null,
    };
    if (parsed.localAccess) {
      // Retired fixture-mode backdoor: strip it from storage instead of honouring it.
      window.localStorage.setItem(KEY, JSON.stringify(session));
    }
    return session;
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
