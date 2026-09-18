"use client";

import { useRef } from "react";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { StatusChip } from "@/components/StatusChip";
import { useDemo } from "@/lib/demo/store";
import { brandLabel, moleculeLabel } from "@/lib/format";
import type { BoxCheckItem, BoxCheckVerdict } from "@/lib/api/types";

const VERDICT: Record<BoxCheckVerdict, { icon: string; label: string; tone: "ok" | "warn" | "danger" }> = {
  matched: { icon: "✓", label: "Matched", tone: "ok" },
  check: { icon: "!", label: "Check", tone: "warn" },
  do_not_take: { icon: "✕", label: "Do not take", tone: "danger" },
};

export default function BoxCheckPage() {
  const cameraRef = useRef<HTMLInputElement>(null);
  const { ready, plan, boxCheckItems, runBoxCheck, addPages } = useDemo();

  if (!ready) return <p>Loading Box Check…</p>;
  if (!plan || plan.status !== "active") {
    return (
      <EmptyState
        title="Activate a plan first"
        body="Box Check compares strips to the active prescription."
        action={plan ? "Go to review" : "Photograph paper"}
        href={plan ? "/review/" : "/upload/"}
        illustration={<ScenePhoto src={ILLUSTRATIONS.boxCheck} />}
      />
    );
  }

  return (
    <section>
      <PageHeader
        eyebrow="Box Check"
        title="Does the box match the paper?"
        description="Photograph the strips you bought. AfterCare never says a strip is safe to take."
        actions={
          <>
            <Button onClick={() => cameraRef.current?.click()}>Photograph strips</Button>
            <Button variant="secondary" onClick={runBoxCheck}>
              Run demo Box Check
            </Button>
          </>
        }
      />

      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        multiple
        className="sr-only"
        aria-label="Photograph medicine strips"
        onChange={(event) => {
          if (event.target.files) addPages(event.target.files);
          event.target.value = "";
        }}
      />

      {boxCheckItems ? (
        <ul className="grid gap-4 md:grid-cols-2">
          {boxCheckItems.map((item, index) => (
            <li key={`${item.reason}-${item.prescribedLineId}-${index}`}>
              <VerdictCard item={item} planBrand={brandFor(plan, item.prescribedLineId)} />
            </li>
          ))}
        </ul>
      ) : (
        <div className="rounded-3xl bg-card p-8">
          <div className="page-scene">
            <ScenePhoto src={ILLUSTRATIONS.boxCheck} />
          </div>
          <p className="text-secondary">No check yet. Photograph strips or run the demo.</p>
        </div>
      )}
    </section>
  );
}

function VerdictCard({ item, planBrand }: { item: BoxCheckItem; planBrand: string }) {
  const meta = VERDICT[item.verdict];
  const toneClass =
    item.verdict === "matched"
      ? "bg-ok-soft"
      : item.verdict === "check"
        ? "bg-warn-soft"
        : "bg-danger-soft";

  return (
    <article className={`h-full rounded-3xl p-6 ${toneClass}`}>
      <StatusChip icon={meta.icon} label={meta.label} tone={meta.tone} />
      <h2 className="mt-4 font-display text-[28px]">{item.stripBrandText ?? planBrand}</h2>
      <p className="mt-2">{item.message}</p>
      {item.stripMolecules.length > 0 ? (
        <p className="mt-2 capitalize text-primary/80">
          {item.stripMolecules.map(moleculeLabel).join(" + ")}
        </p>
      ) : null}
    </article>
  );
}

function brandFor(plan: { medicines: { lineId: string; brand: string | null }[] }, lineId: string | null) {
  if (!lineId) return "Unmatched strip";
  return brandLabel(plan.medicines.find((medicine) => medicine.lineId === lineId)?.brand ?? null);
}
