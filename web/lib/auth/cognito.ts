"use client";

import { Amplify } from "aws-amplify";
import {
  autoSignIn,
  confirmSignIn,
  confirmSignUp,
  fetchAuthSession,
  signIn,
  signOut,
  signUp,
} from "aws-amplify/auth";

let configured = false;

export function configureAuth(): void {
  if (configured || typeof window === "undefined") return;
  const userPoolId = process.env.NEXT_PUBLIC_COGNITO_POOL_ID;
  const userPoolClientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID;
  if (!userPoolId || !userPoolClientId) return;
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
        loginWith: { email: true },
      },
    },
  });
  configured = true;
}

export function authConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_COGNITO_POOL_ID && process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID);
}

export async function getIdToken(): Promise<string | null> {
  configureAuth();
  if (!authConfigured()) return null;
  try {
    const session = await fetchAuthSession();
    return session.tokens?.idToken?.toString() ?? null;
  } catch {
    return null;
  }
}

function randomPassword(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(18));
  const body = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${body}Aa1!`;
}

export async function startOwnerSignIn(email: string): Promise<"code" | "confirm_sign_up"> {
  configureAuth();
  const username = email.trim().toLowerCase();
  const result = await signIn({
    username,
    options: {
      authFlowType: "USER_AUTH",
      preferredChallenge: "EMAIL_OTP",
    },
  });
  if (result.nextStep.signInStep === "CONFIRM_SIGN_UP") return "confirm_sign_up";
  return "code";
}

export async function startOwnerSignUp(email: string): Promise<void> {
  configureAuth();
  const username = email.trim().toLowerCase();
  await signUp({
    username,
    password: randomPassword(),
    options: {
      userAttributes: { email: username },
      autoSignIn: { authFlowType: "USER_AUTH" },
    },
  });
}

export async function confirmOwnerSignUp(email: string, code: string): Promise<void> {
  configureAuth();
  const username = email.trim().toLowerCase();
  const result = await confirmSignUp({ username, confirmationCode: code.trim() });
  if (result.nextStep.signUpStep === "COMPLETE_AUTO_SIGN_IN") {
    await autoSignIn();
    return;
  }
  await startOwnerSignIn(username);
}

export async function confirmOwnerCode(code: string): Promise<void> {
  configureAuth();
  const result = await confirmSignIn({ challengeResponse: code.trim() });
  if (result.nextStep.signInStep !== "DONE" && !result.isSignedIn) {
    throw new Error("That code did not finish sign-in. Try the latest email.");
  }
}

export async function ownerSignOut(): Promise<void> {
  configureAuth();
  try {
    await signOut();
  } catch {
    // Local state is still cleared by the caller.
  }
}

export function explainAuthError(error: unknown): string {
  const name = error && typeof error === "object" && "name" in error ? String(error.name) : "";
  const message = error instanceof Error ? error.message : "";
  if (name === "UserNotFoundException" || /user does not exist/i.test(message)) {
    return "No account for that email yet. Create an account.";
  }
  if (name === "UsernameExistsException" || /already exists/i.test(message)) {
    return "That email already has an account. Email a sign-in code instead.";
  }
  if (name === "CodeMismatchException" || /code mismatch/i.test(message)) {
    return "That code does not match. Check the latest email.";
  }
  if (name === "ExpiredCodeException" || /expired/i.test(message)) {
    return "That code has expired. Ask for a new one.";
  }
  if (name === "NotAuthorizedException") {
    return "Sign-in was rejected. Try again, or create an account.";
  }
  if (name === "LimitExceededException" || /attempt limit/i.test(message)) {
    return "Too many tries. Wait a minute and try again.";
  }
  return "Sign-in did not work. Try again in a minute.";
}
