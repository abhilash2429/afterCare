"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { ErrorNote } from "@/components/ErrorNote";
import { PageHeader } from "@/components/PageHeader";
import { QrCode } from "@/components/QrCode";
import { useApp } from "@/lib/app/store";
import {
  confirmOwnerCode,
  confirmOwnerSignUp,
  explainAuthError,
  startOwnerSignIn,
  startOwnerSignUp,
} from "@/lib/auth/cognito";
import { bi, CIRCLE_LANG_OPTIONS, langNative, scriptClass, type UiLang } from "@/lib/copy";
import type { Invite } from "@/lib/api/types";

export default function SetupPage() {
  const router = useRouter();
  const { demo, signedIn, circleId, createCircle, inviteCaregiver, error, setError, refresh, role, uiLang, ready } =
    useApp();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "signup-code" | "signin-code">("email");
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("Family");
  const [language, setLanguage] = useState<UiLang>("kn");
  const [invite, setInvite] = useState<Invite | null>(null);

  const ownerReady = demo || signedIn;

  if (!ready) return <p>{bi("loading", uiLang)}</p>;

  async function sendSignIn() {
    setBusy(true);
    setError(null);
    try {
      const next = await startOwnerSignIn(email);
      setStep(next === "confirm_sign_up" ? "signup-code" : "signin-code");
    } catch (err) {
      setError(explainAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  async function sendSignUp() {
    setBusy(true);
    setError(null);
    try {
      await startOwnerSignUp(email);
      setStep("signup-code");
    } catch (err) {
      setError(explainAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  async function submitCode() {
    const pin = code.trim();
    setBusy(true);
    setError(null);
    try {
      if (step === "signup-code") await confirmOwnerSignUp(email, pin);
      else await confirmOwnerCode(pin);
      await refresh();
    } catch (err) {
      setError(explainAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  async function onCreateCircle() {
    setBusy(true);
    const id = await createCircle(name.trim() || "Family", language);
    setBusy(false);
    if (id) setInvite(null);
  }

  async function onInvite() {
    setBusy(true);
    const next = await inviteCaregiver();
    setBusy(false);
    if (next) setInvite(next);
  }

  async function shareInvite() {
    if (!invite) return;
    if (navigator.share) {
      await navigator.share({ title: "AfterCare invite", url: invite.url, text: "Join this care circle." }).catch(() => undefined);
    } else {
      await navigator.clipboard.writeText(invite.url);
    }
  }

  return (
    <section>
      <PageHeader eyebrow="setupEyebrow" title="setupTitle" description="setupDesc" />
      {demo ? (
        <p className="mb-6 rounded-2xl bg-warn-soft px-4 py-3 text-warn">{bi("demoOn", uiLang)}</p>
      ) : null}
      <ErrorNote message={error} />

      {!demo && !ownerReady ? (
        <article className="app-panel mb-6 rounded-3xl bg-card p-6">
          <h2 className="font-semibold">
            <Bilingual k="ownerEmail" lang={uiLang} />
          </h2>
          <label className="mt-4 block">
            <span className="field-label">
              <Bilingual k="email" lang={uiLang} />
            </span>
            <input
              className="field-input"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="mt-4 block">
            <span className="field-label">
              <Bilingual k="codeFromEmail" lang={uiLang} />
            </span>
            <input
              className="field-input"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 8))}
            />
          </label>
          <div className="app-actions mt-5">
            <Button onClick={sendSignIn} disabled={busy || !email.includes("@")}>
              <Bilingual k="emailMeCode" lang={uiLang} />
            </Button>
            <Button variant="ghost" onClick={sendSignUp} disabled={busy || !email.includes("@")}>
              <Bilingual k="createAccount" lang={uiLang} />
            </Button>
            <Button onClick={submitCode} disabled={busy || code.trim().length < 4}>
              <Bilingual k="confirmCode" lang={uiLang} />
            </Button>
          </div>
        </article>
      ) : null}

      {(demo || ownerReady) && !circleId ? (
        <article className="app-panel mb-6 rounded-3xl bg-card p-6">
          <h2 className="font-semibold">
            <Bilingual k="circle" lang={uiLang} />
          </h2>
          <label className="mt-4 block">
            <span className="field-label">
              <Bilingual k="name" lang={uiLang} />
            </span>
            <input className="field-input" value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <fieldset className="mt-4">
            <legend className="field-label">
              <Bilingual k="language" lang={uiLang} />
            </legend>
            <div className="slot-dots">
              {CIRCLE_LANG_OPTIONS.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`slot-dot${language === item ? " is-on" : ""}`}
                  onClick={() => setLanguage(item)}
                >
                  <span className={scriptClass(item)}>{langNative(item)}</span>
                </button>
              ))}
            </div>
          </fieldset>
          <div className="mt-5">
            <Button onClick={onCreateCircle} disabled={busy}>
              <Bilingual k="createCircle" lang={uiLang} />
            </Button>
          </div>
        </article>
      ) : null}

      {circleId ? (
        <article className="app-panel rounded-3xl bg-card p-6">
          <h2 className="font-semibold">
            <Bilingual k="inviteCaregiverTitle" lang={uiLang} />
          </h2>
          <p className="muted mt-2">
            <Bilingual k="inviteBody" lang={uiLang} />
          </p>
          <div className="app-actions mt-5">
            <Button onClick={onInvite} disabled={busy || role === "caregiver"}>
              <Bilingual k="makeInvite" lang={uiLang} />
            </Button>
            <Button variant="secondary" onClick={() => router.push("/upload/")}>
              <Bilingual k="photographPaper" lang={uiLang} />
            </Button>
          </div>
          {invite ? (
            <div className="app-invite">
              <QrCode value={invite.url} label="Caregiver invite QR code" />
              <p className="app-url">{invite.url}</p>
              <Button variant="ghost" onClick={shareInvite}>
                <Bilingual k="shareInvite" lang={uiLang} />
              </Button>
            </div>
          ) : null}
        </article>
      ) : null}
    </section>
  );
}
