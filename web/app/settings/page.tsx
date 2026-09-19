"use client";

import { useRouter } from "next/navigation";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { PageHeader } from "@/components/PageHeader";
import { PushPrompt } from "@/components/PushPrompt";
import { COPY, LANG_OPTIONS, bi, langNative, scriptClass } from "@/lib/copy";
import { useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";

export default function SettingsPage() {
  const router = useRouter();
  const { reset, plan, circle, role, demo, signOutAll, queuedDoseIds, uiLang, setUiLang } = useApp();
  const { isApp } = useAppView();

  async function onSignOut() {
    await signOutAll();
    reset();
    router.push(isApp ? "/app/" : "/");
  }

  return (
    <section>
      <PageHeader
        eyebrow="settings"
        title="privacyTitle"
        description={demo ? "privacyDemo" : "privacyBody"}
        actions={
          <Button variant="danger" onClick={onSignOut}>
            <Bilingual k="deleteDevice" lang={uiLang} />
          </Button>
        }
      />

      <div className={`grid gap-5 ${isApp ? "" : "md:grid-cols-2"}`}>
        <article className="app-panel rounded-3xl bg-card p-6">
          <h2 className="font-semibold">
            <Bilingual k="language" lang={uiLang} />
          </h2>
          <p className="muted mt-2">
            <Bilingual k="languageHint" lang={uiLang} />
          </p>
          <div className="slot-dots mt-4">
            {LANG_OPTIONS.map((item) => (
              <button
                key={item}
                type="button"
                className={`slot-dot${uiLang === item ? " is-on" : ""}`}
                onClick={() => setUiLang(item)}
              >
                <span className={scriptClass(item)}>{langNative(item)}</span>
              </button>
            ))}
          </div>
        </article>
        <article className="app-panel rounded-3xl bg-card p-6">
          <h2 className="font-semibold">
            <Bilingual k="safety" lang={uiLang} />
          </h2>
          <p className={`mt-2 ${scriptClass(uiLang)}`}>{COPY.disclaimer[uiLang]}</p>
        </article>
        <article className="app-panel rounded-3xl bg-card p-6">
          <h2 className="font-semibold">
            <Bilingual k="currentPlan" lang={uiLang} />
          </h2>
          <p className="mt-2 text-secondary">
            {plan ? `Plan ${plan.planId} · ${plan.status}` : bi("noPlanDevice", uiLang)}
          </p>
          <p className="muted mt-2">
            {circle ? `${circle.name ?? "Circle"} · ${role ?? "unknown role"}` : bi("noCircleDevice", uiLang)}
          </p>
          {queuedDoseIds.length > 0 ? (
            <p className="mt-2 text-warn">
              {queuedDoseIds.length} · {bi("queued", uiLang)}
            </p>
          ) : null}
        </article>
        <PushPrompt />
      </div>
    </section>
  );
}
