"use client";

import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { SLOT_LABELS } from "@/lib/copy";
import { brandLabel, foodLabel } from "@/lib/format";
import { useDemo } from "@/lib/demo/store";
import type { Slot } from "@/lib/api/types";

const SLOTS: Slot[] = ["morning", "noon", "night", "bedtime"];

export default function FridgeSheetPage() {
  const { ready, plan } = useDemo();

  if (!ready) return <p>Loading fridge sheet…</p>;
  if (!plan) {
    return (
      <EmptyState
        title="Nothing to print yet"
        body="Photograph a discharge summary first."
        action="Photograph paper"
        href="/upload/"
        illustration={<ScenePhoto src={ILLUSTRATIONS.reminder} />}
      />
    );
  }

  const scheduled = plan.medicines.filter((medicine) => !medicine.prn);
  const prn = plan.medicines.filter((medicine) => medicine.prn);

  return (
    <section>
      <PageHeader
        eyebrow="Fridge sheet"
        title="Print this and keep it on the fridge"
        actions={<Button onClick={() => window.print()}>Print or save PDF</Button>}
      />
      <div className="page-scene mb-8 print:hidden">
        <ScenePhoto src={ILLUSTRATIONS.reminder} />
      </div>

      <div className="rounded-[28px] border-2 border-primary bg-white p-8">
        <p className="font-display text-[32px]">AfterCare schedule</p>
        <table className="mt-6 w-full text-left">
          <thead>
            <tr>
              <th className="border-b border-primary py-3">Medicine</th>
              {SLOTS.map((slot) => (
                <th key={slot} className="border-b border-primary py-3 text-center">
                  {SLOT_LABELS[slot].en}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {scheduled.map((medicine) => (
              <tr key={medicine.lineId}>
                <td className="border-b border-primary/20 py-3">
                  <strong>{brandLabel(medicine.brand)}</strong>
                  <div>{foodLabel(medicine.foodRelation)}</div>
                </td>
                {SLOTS.map((slot) => (
                  <td key={slot} className="border-b border-primary/20 py-3 text-center">
                    {medicine.slots.includes(slot) ? "Take" : "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {prn.length > 0 ? (
          <div className="mt-6">
            <p className="font-semibold">Only when needed</p>
            {prn.map((medicine) => (
              <p key={medicine.lineId}>
                {brandLabel(medicine.brand)} — {medicine.prnCondition ?? "ask your doctor"}
              </p>
            ))}
          </div>
        ) : null}
        <p className="mt-6">AfterCare re-displays what your doctor wrote. It never changes a dose.</p>
      </div>
    </section>
  );
}
