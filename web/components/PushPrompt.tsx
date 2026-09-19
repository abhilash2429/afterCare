"use client";

import { useState } from "react";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { useApp } from "@/lib/app/store";
import { api } from "@/lib/api/client";
import { explainError } from "@/lib/app/errors";
import { bi } from "@/lib/copy";
import { isIosSafari, isStandalone, subscribeWebPush } from "@/lib/push/register";

export function PushPrompt() {
  const { circleId, demo, setError, uiLang } = useApp();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const ios = isIosSafari();
  const standalone = isStandalone();

  if (!circleId || demo) return null;
  if (!("Notification" in window) || !("serviceWorker" in navigator)) return null;

  async function onTap() {
    if (!circleId || (ios && !standalone)) return;
    setBusy(true);
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setError("Notifications were not allowed. You can enable them later in Settings.");
        return;
      }
      const sub = await subscribeWebPush();
      await api.registerPush(circleId, sub);
      setDone(true);
    } catch (err) {
      setError(explainError(err, "Turning on reminders"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="app-panel rounded-3xl bg-card p-6">
      <h2 className="font-semibold">
        <Bilingual k="remindersTitle" lang={uiLang} />
      </h2>
      {ios && !standalone ? (
        <p className="mt-2">
          On iPhone, add AfterCare to the Home Screen first (Share → Add to Home Screen), then open
          it from the icon. iOS only allows reminders from an installed app.
        </p>
      ) : done ? (
        <p className="mt-2 text-ok">{bi("remindersOn", uiLang)}</p>
      ) : (
        <>
          <p className="muted mt-2">{bi("remindersHint", uiLang)}</p>
          <div className="mt-4">
            <Button onClick={onTap} disabled={busy}>
              <Bilingual k="turnOnReminders" lang={uiLang} />
            </Button>
          </div>
        </>
      )}
    </article>
  );
}
