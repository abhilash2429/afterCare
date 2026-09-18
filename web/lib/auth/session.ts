export type Session = {
  token: string;
  role: "owner" | "caregiver";
  circleId: string;
};

const KEY = "aftercare-session";

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

export function getSessionToken(): string | null {
  return getSession()?.token ?? null;
}

export function setSession(session: Session): void {
  window.sessionStorage.setItem(KEY, JSON.stringify(session));
}

export function clearSession(): void {
  window.sessionStorage.removeItem(KEY);
}
