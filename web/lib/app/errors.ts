import { ApiRequestError } from "@/lib/api/client";
import type { ApiErrorCode } from "@/lib/api/types";

export const EXTRACTION_FAILED =
  "We couldn't read this photo. Retake it in good light, flat, whole page in frame.";

export const INVITE_USED =
  "This invite link has already been used or expired. Ask for a new one.";

export const FORBIDDEN = "You don't have access to this.";

export const AUTH_DOWN = "Sign-in check is down, try again in a minute.";

export function messageForCode(code: ApiErrorCode, fallback: string, context?: "invite"): string {
  if (code === "unauthorized") {
    return "Sign in again, or ask for a new invite.";
  }
  if (code === "forbidden") return FORBIDDEN;
  if (code === "not_found" && context === "invite") return INVITE_USED;
  if (code === "extraction_failed") return EXTRACTION_FAILED;
  if (code === "auth_unavailable") return AUTH_DOWN;
  return fallback;
}

export function explainError(error: unknown, action: string): string {
  if (error instanceof ApiRequestError) {
    if (error.code === "validation_failed") return error.message;
    if (error.code === "extraction_failed") return EXTRACTION_FAILED;
    if (error.code === "conflict") return "This is already active. Reloading.";
    if (error.code === "unauthorized") {
      return `${action} needs you to sign in again (owner) or ask for a new invite (caregiver).`;
    }
    if (error.code === "forbidden") return FORBIDDEN;
    if (error.code === "auth_unavailable") return AUTH_DOWN;
    if (error.message) return `${action} failed. ${error.message}`;
  }
  if (error instanceof DOMException && error.name === "AbortError") {
    return `${action} took too long. Try again in good light, with the whole page in frame.`;
  }
  return `${action} failed. Check the connection and try again.`;
}
