"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { StatusChip } from "@/components/StatusChip";
import { GIVEN, SLOT_LABELS } from "@/lib/copy";
import { brandLabel, foodLabel } from "@/lib/format";
import { useDemo } from "@/lib/demo/store";
import type { Slot } from "@/lib/api/types";

const SLOTS: Slot[] = ["morning", "noon", "night", "bedtime"];

export default function SchedulePage() {
  const router = useRouter();
  const { ready, plan, doses, markGiven } = useDemo();

  if (!ready) return <p>Loading schedule…</p>;
  if (!plan || plan.status !== "active") {
    return (
      <EmptyState
        title="No active schedule"
        body={plan ? "Review and activate the draft plan first." : "Photograph a discharge summary first."}
        action={plan ? "Go to review" : "Photograph paper"}
        href={plan ? "/review/" : "/upload/"}
        illustration={<ScenePhoto src={ILLUSTRATIONS.schedule} />}
      />
    );
  }

  const scheduled = plan.medicines.filter((medicine) => !medicine.prn);
  const prn = plan.medicines.filter((medicine) => medicine.prn);

  return (
    <section>
      <PageHeader
        eyebrow="Today"
        title="Medicine schedule"
        description="One Given action per time slot, not per medicine."
        actions={
          <Button variant="ghost" onClick={() => router.push("/fridge-sheet/")}>
            Open fridge sheet
          </Button>
        }
      />
      <div className="page-scene mb-8">
        <ScenePhoto src={ILLUSTRATIONS.schedule} />
      </div>

      <div className="overflow-hidden rounded-[28px] border border-card">
        <table className="w-full text-left">
          <thead className="bg-card">
            <tr>
              <th className="px-5 py-4 font-semibold">Medicine</th>
              {SLOTS.map((slot) => (
                <th key={slot} className="px-5 py-4 text-center font-semibold">
                  <span className="block">{SLOT_LABELS[slot].en}</span>
                  <span className="muted block font-normal">{plan.slotTimes[slot]}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {scheduled.map((medicine) => (
              <tr key={medicine.lineId} className="border-t border-card">
                <th className="px-5 py-4 align-top">
                  <p className="font-semibold">{brandLabel(medicine.brand)}</p>
                  <p className="muted font-normal">
                    {foodIcon(medicine.foodRelation)} {foodLabel(medicine.foodRelation)}
                  </p>
                </th>
                {SLOTS.map((slot) => {
                  const on = medicine.slots.includes(slot);
                  return (
                    <td key={slot} className="px-5 py-4 text-center">
                      <span className="sr-only">
                        {on ? `Take in the ${slot}` : `Not scheduled in the ${slot}`}
                      </span>
                      <span
                        aria-hidden="true"
                        className={`inline-block h-5 w-5 rounded-full ${
                          on ? "bg-secondary" : "border-2 border-primary/25 bg-white"
                        }`}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-8 grid gap-5 md:grid-cols-3">
        {doses.map((dose) => {
          const names = dose.medicineLineIds
            .map((id) => brandLabel(plan.medicines.find((medicine) => medicine.lineId === id)?.brand ?? null))
            .join(", ");
          const given = dose.status === "given";
          const missed = dose.status === "missed";
          return (
            <article key={dose.doseId} className="rounded-3xl bg-card p-6">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-display text-[28px]">
                  {SLOT_LABELS[dose.slot].en} · {plan.slotTimes[dose.slot]}
                </h2>
                {given ? (
                  <StatusChip icon="✓" label={GIVEN.en} tone="ok" />
                ) : missed ? (
                  <StatusChip icon="✕" label="Missed" tone="danger" />
                ) : (
                  <StatusChip icon="○" label="Due" />
                )}
              </div>
              <p className="mt-3">{names}</p>
              <p className="font-kannada muted mt-1">{SLOT_LABELS[dose.slot].kn}</p>
              {!given ? (
                <div className="mt-5">
                  <Button onClick={() => markGiven(dose.doseId)}>
                    {GIVEN.en} · {GIVEN.kn}
                  </Button>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      {prn.length > 0 ? (
        <section className="mt-10">
          <h2 className="font-display text-[32px]">Only when needed</h2>
          <ul className="mt-4 grid gap-4 md:grid-cols-2">
            {prn.map((medicine) => (
              <li key={medicine.lineId} className="rounded-3xl bg-card p-6">
                <p className="font-semibold">{brandLabel(medicine.brand)}</p>
                <p className="muted mt-1">
                  {medicine.prnCondition ?? "Condition not stated. Ask your doctor."}
                </p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

function foodIcon(relation: string): string {
  if (relation === "before") return "○";
  if (relation === "after") return "◉";
  return "–";
}
