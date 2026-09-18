"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { StatusChip } from "@/components/StatusChip";
import { useDemo } from "@/lib/demo/store";
import {
  brandLabel,
  durationLabel,
  foodLabel,
  frequencyLabel,
  medicineMolecules,
} from "@/lib/format";

export default function ReviewPage() {
  const router = useRouter();
  const { ready, plan, confirmedLineIds, confirmMedicine, activate } = useDemo();

  if (!ready) return <p>Loading plan…</p>;
  if (!plan) {
    return (
      <EmptyState
        title="No plan to review"
        body="Photograph a discharge summary first."
        action="Go to upload"
        href="/upload/"
        illustration={<ScenePhoto src={ILLUSTRATIONS.review} />}
      />
    );
  }

  const unresolved = plan.medicines.filter(
    (medicine) => medicine.needsConfirmation && !confirmedLineIds.includes(medicine.lineId),
  );

  function onActivate() {
    if (unresolved.length > 0) return;
    activate();
    router.push("/schedule/");
  }

  return (
    <section>
      <PageHeader
        eyebrow="Review and confirm"
        title="Check every medicine"
        description="Amber lines stay blocked until you confirm them. AfterCare never fills a missing dose."
        actions={
          <Button onClick={onActivate} disabled={unresolved.length > 0}>
            Activate schedule
          </Button>
        }
      />
      <div className="page-scene mb-8">
        <ScenePhoto src={ILLUSTRATIONS.review} />
      </div>

      {unresolved.length > 0 ? (
        <p className="mb-6 rounded-2xl bg-warn-soft px-4 py-3 text-warn">
          Confirm {unresolved.length} amber {unresolved.length === 1 ? "line" : "lines"} before
          activating.
        </p>
      ) : null}

      {plan.followUp?.date || plan.followUp?.with ? (
        <article className="mb-6 rounded-3xl bg-card p-6">
          <h2 className="font-semibold">Follow-up</h2>
          <p className="mt-1">
            {plan.followUp.with ?? "Clinic not stated"}
            {plan.followUp.date ? ` · ${plan.followUp.date}` : ""}
          </p>
        </article>
      ) : null}

      <ul className="grid gap-5 md:grid-cols-2">
        {plan.medicines.map((medicine) => {
          const needsConfirm = medicine.needsConfirmation && !confirmedLineIds.includes(medicine.lineId);
          return (
            <li key={medicine.lineId}>
              <article
                className={`h-full rounded-3xl p-6 ${needsConfirm ? "bg-warn-soft" : "bg-card"}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-display text-[28px]">{brandLabel(medicine.brand)}</h2>
                  {needsConfirm ? (
                    <StatusChip icon="!" label="Confirm" tone="warn" />
                  ) : (
                    <StatusChip icon="✓" label="Checked" tone="ok" />
                  )}
                  {medicine.prn ? <StatusChip icon="SOS" label="Only when needed" /> : null}
                </div>
                <p className="mt-2 capitalize">{medicineMolecules(medicine)}</p>
                <dl className="mt-4 grid grid-cols-2 gap-3">
                  <div>
                    <dt className="muted font-semibold">Frequency</dt>
                    <dd>{frequencyLabel(medicine.frequency)}</dd>
                  </div>
                  <div>
                    <dt className="muted font-semibold">Food</dt>
                    <dd>{foodLabel(medicine.foodRelation)}</dd>
                  </div>
                  <div>
                    <dt className="muted font-semibold">Duration</dt>
                    <dd>{durationLabel(medicine.durationDays)}</dd>
                  </div>
                  <div>
                    <dt className="muted font-semibold">Form</dt>
                    <dd className="capitalize">{medicine.form ?? "Not stated"}</dd>
                  </div>
                </dl>
                <p className="mt-4 rounded-2xl bg-white px-3 py-2 text-primary/80">
                  {medicine.rawText}
                </p>
                {needsConfirm ? (
                  <div className="mt-5">
                    <Button onClick={() => confirmMedicine(medicine.lineId)}>
                      I checked this line
                    </Button>
                  </div>
                ) : null}
              </article>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

