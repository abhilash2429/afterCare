"use client";

import { useRef } from "react";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorNote } from "@/components/ErrorNote";
import { PageHeader } from "@/components/PageHeader";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { StatusChip } from "@/components/StatusChip";
import { useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";
import { bi, type CopyKey } from "@/lib/copy";
import { brandLabel, moleculeLabel } from "@/lib/format";
import type { BoxCheckItem, BoxCheckVerdict } from "@/lib/api/types";

const VERDICT: Record<BoxCheckVerdict, { icon: string; k: CopyKey; tone: "ok" | "warn" | "danger" }> = {
  matched: { icon: "✓", k: "matches", tone: "ok" },
  check: { icon: "!", k: "check", tone: "warn" },
  do_not_take: { icon: "✕", k: "doNotTake", tone: "danger" },
};

export default function BoxCheckPage() {
  const cameraRef = useRef<HTMLInputElement>(null);
  const { isApp } = useAppView();
  const {
    ready,
    plan,
    stripPages,
    boxCheckItems,
    boxChecking,
    runBoxCheck,
    addPages,
    removePage,
    error,
    setError,
    uiLang,
  } = useApp();

  if (!ready) return <p>{bi("loading", uiLang)}</p>;
  if (!plan || plan.status !== "active") {
    return (
      <EmptyState
        title="activatePlanFirst"
        body="boxCheckNeedPlan"
        action={plan ? "goToReview" : "photographPaper"}
        href={plan ? "/review/" : "/upload/"}
        illustration={<ScenePhoto src={ILLUSTRATIONS.boxCheck} />}
      />
    );
  }

  if (boxChecking) {
    return (
      <section className="flex min-h-[60vh] flex-col items-center justify-center text-center">
        <div className="page-scene page-scene-center">
          <ScenePhoto src={ILLUSTRATIONS.boxCheck} />
        </div>
        <h1 className={`font-display text-primary ${isApp ? "text-[26px] leading-snug" : "text-[40px]"}`}>{bi("checkingStrips", uiLang)}</h1>
        <p className="muted mt-3">{bi("canTake40", uiLang)}</p>
      </section>
    );
  }

  return (
    <section>
      <PageHeader
        eyebrow="boxCheck"
        title="boxMatch"
        description="boxCheckDesc"
        actions={
          <div className={isApp ? "app-actions" : "flex flex-wrap gap-3"}>
            <Button onClick={() => cameraRef.current?.click()}>
              <Bilingual k="photographStrips" lang={uiLang} />
            </Button>
            <Button variant="secondary" onClick={() => void runBoxCheck()} disabled={stripPages.length === 0}>
              <Bilingual k="checkPhotos" lang={uiLang} />
            </Button>
          </div>
        }
      />
      <ErrorNote message={error} />

      <input
        ref={cameraRef}
        type="file"
        accept="image/jpeg,image/png"
        capture="environment"
        multiple
        className="sr-only"
        aria-label="Photograph medicine strips"
        onChange={(event) => {
          if (event.target.files) setError(addPages(event.target.files, "strips"));
          event.target.value = "";
        }}
      />

      {stripPages.length > 0 ? (
        <ul className={`mb-8 grid grid-cols-2 gap-4 ${isApp ? "" : "md:grid-cols-4"}`}>
          {stripPages.map((page, index) => (
            <li key={page.id} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={page.previewUrl} alt={`Strip photo ${index + 1}`} className="h-40 w-full rounded-2xl object-cover" />
              <button
                type="button"
                onClick={() => removePage(page.id, "strips")}
                className="absolute right-2 top-2 rounded-full bg-primary px-3 py-1 text-[16px] text-white"
              >
                {bi("remove", uiLang)}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {boxCheckItems ? (
        <ul className={`grid gap-4 ${isApp ? "" : "md:grid-cols-2"}`}>
          {boxCheckItems.map((item, index) => (
            <li key={`${item.reason}-${item.prescribedLineId}-${index}`}>
              <VerdictCard item={item} planBrand={brandFor(plan, item.prescribedLineId, uiLang)} />
            </li>
          ))}
        </ul>
      ) : (
        <div>
          <div className="page-scene">
            <ScenePhoto src={ILLUSTRATIONS.boxCheck} />
          </div>
          <p className="text-secondary">{bi("noCheckYet", uiLang)}</p>
        </div>
      )}
    </section>
  );
}

function VerdictCard({ item, planBrand }: { item: BoxCheckItem; planBrand: string }) {
  const { uiLang } = useApp();
  const { isApp } = useAppView();
  const meta = VERDICT[item.verdict];
  const toneClass =
    item.verdict === "matched" ? "bg-ok-soft" : item.verdict === "check" ? "bg-warn-soft" : "bg-danger-soft";

  return (
    <article className={`app-panel h-full rounded-3xl p-6 ${toneClass}`}>
      <StatusChip icon={meta.icon} label={bi(meta.k, uiLang)} tone={meta.tone} />
      <h2 className={`mt-4 font-display leading-snug ${isApp ? "text-[22px]" : "text-[28px]"}`}>
        {item.stripBrandText ?? planBrand}
      </h2>
      {item.message ? <p className="mt-2">{item.message}</p> : null}
      {item.stripMolecules.length > 0 ? (
        <p className="mt-2 capitalize text-primary/80">{item.stripMolecules.map(moleculeLabel).join(" + ")}</p>
      ) : null}
    </article>
  );
}

function brandFor(
  plan: { medicines: { lineId: string; brand: string | null }[] },
  lineId: string | null,
  uiLang: "en" | "hi" | "kn" | "te",
) {
  if (!lineId) return bi("unmatchedStrip", uiLang);
  return brandLabel(plan.medicines.find((medicine) => medicine.lineId === lineId)?.brand ?? null);
}
