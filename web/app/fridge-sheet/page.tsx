"use client";

import { useState } from "react";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { DoseMatrix } from "@/components/DoseMatrix";
import { EmptyState } from "@/components/EmptyState";
import { ErrorNote } from "@/components/ErrorNote";
import { PageHeader } from "@/components/PageHeader";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { bi, COPY } from "@/lib/copy";
import { brandLabel, foodKey, foodLabel } from "@/lib/format";
import { downloadBlob, renderFridgePng, shareFridgePng } from "@/lib/fridge/render";
import { useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";
import type { Slot } from "@/lib/api/types";

const SLOTS: Slot[] = ["morning", "noon", "night", "bedtime"];

export default function FridgeSheetPage() {
  const { ready, plan, uiLang } = useApp();
  const { isApp } = useAppView();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!ready) return <p>{bi("loading", uiLang)}</p>;
  if (!plan) {
    return (
      <EmptyState
        title="nothingToPrint"
        body="photographFirst"
        action="photographPaper"
        href="/upload/"
        illustration={<ScenePhoto src={ILLUSTRATIONS.reminder} />}
      />
    );
  }
  if (plan.status !== "active") {
    return (
      <EmptyState
        title="nothingToPrint"
        body="reviewActivate"
        action="goToReview"
        href="/review/"
        illustration={<ScenePhoto src={ILLUSTRATIONS.reminder} />}
      />
    );
  }

  const scheduled = plan.medicines.filter((medicine) => !medicine.prn);
  const prn = plan.medicines.filter((medicine) => medicine.prn);

  async function exportSheet() {
    if (!plan) return;
    setBusy(true);
    setError(null);
    try {
      const blob = await renderFridgePng(plan);
      downloadBlob(blob, "aftercare-fridge-sheet.png");
      await shareFridgePng(blob);
    } catch {
      setError("Could not make the fridge sheet. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="fridgeSheet"
        title="printFridgeTitle"
        actions={
          <Button onClick={exportSheet} disabled={busy}>
            <Bilingual k="downloadPng" lang={uiLang} />
          </Button>
        }
      />
      <ErrorNote message={error} />
      {isApp ? null : (
        <div className="page-scene mb-8 print:hidden">
          <ScenePhoto src={ILLUSTRATIONS.reminder} />
        </div>
      )}

      <div className="app-panel rounded-[28px] border-2 border-primary bg-white p-8">
        <p className={isApp ? "font-display text-[22px] leading-snug" : "font-display text-[32px]"}>{COPY.aftercareSchedule[uiLang]}</p>
        {isApp ? (
          <div className="mt-4">
            <DoseMatrix medicines={scheduled} />
          </div>
        ) : (
          <table className="mt-6 w-full text-left">
            <thead>
              <tr>
                <th className="border-b border-primary py-3">
                  <Bilingual k="medicine" lang={uiLang} stacked />
                </th>
                {SLOTS.map((slot) => (
                  <th key={slot} className="border-b border-primary py-3 text-center">
                    <Bilingual k={slot} lang={uiLang} stacked />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scheduled.map((medicine) => (
                <tr key={medicine.lineId}>
                  <td className="border-b border-primary/20 py-3">
                    <strong>{brandLabel(medicine.brand)}</strong>
                    <div>
                      <Bilingual k={foodKey(medicine.foodRelation)} lang={uiLang} />
                    </div>
                  </td>
                  {SLOTS.map((slot) => (
                    <td key={slot} className="border-b border-primary/20 py-3 text-center">
                      <Bilingual k={medicine.slots.includes(slot) ? "take" : "skip"} lang={uiLang} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {prn.length > 0 ? (
          <div className="mt-6">
            <p className="font-semibold">
              <Bilingual k="onlyWhenNeeded" lang={uiLang} />
            </p>
            {prn.map((medicine) => (
              <p key={medicine.lineId}>
                {brandLabel(medicine.brand)} — {medicine.prnCondition ?? foodLabel("unspecified", uiLang)}
              </p>
            ))}
          </div>
        ) : null}
        <p className="mt-6">{COPY.disclaimer[uiLang]}</p>
      </div>
    </section>
  );
}
