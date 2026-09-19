"use client";

import { useRouter } from "next/navigation";
import { AudioPlayer } from "@/components/AudioPlayer";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { DoseMatrix } from "@/components/DoseMatrix";
import { EmptyState } from "@/components/EmptyState";
import { ErrorNote } from "@/components/ErrorNote";
import { PageHeader } from "@/components/PageHeader";
import { PlateMark } from "@/components/PlateMark";
import { StatusChip } from "@/components/StatusChip";
import { ILLUSTRATIONS, ScenePhoto } from "@/components/marketing/illustrations";
import { bi, COPY, type CopyKey } from "@/lib/copy";
import { brandLabel, foodKey } from "@/lib/format";
import { useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";
import type { Slot } from "@/lib/api/types";

const SLOTS: Slot[] = ["morning", "noon", "night", "bedtime"];

export default function SchedulePage() {
  const router = useRouter();
  const { isApp } = useAppView();
  const { ready, plan, doses, markGiven, queuedDoseIds, audio, loadAudio, error, circleId, uiLang } = useApp();

  if (!ready) return <p>{bi("loading", uiLang)}</p>;
  if (!circleId) {
    return (
      <EmptyState
        title="noCircleTitle"
        body="noCircleBody"
        action="setUp"
        href="/setup/"
        illustration={<ScenePhoto src={ILLUSTRATIONS.schedule} />}
      />
    );
  }
  if (!plan || plan.status !== "active") {
    return (
      <EmptyState
        title="noScheduleTitle"
        body={plan ? "reviewActivate" : "photographFirst"}
        action={plan ? "goToReview" : "photographPaper"}
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
        eyebrow="today"
        title="medicineSchedule"
        description="oneGiven"
        actions={
          <div className={isApp ? "app-actions" : "flex flex-wrap gap-3"}>
            <Button variant="ghost" onClick={() => router.push("/fridge-sheet/")}>
              <Bilingual k="openFridge" lang={uiLang} />
            </Button>
            <Button variant="ghost" onClick={() => router.push("/family/")}>
              <Bilingual k="familyView" lang={uiLang} />
            </Button>
          </div>
        }
      />
      <ErrorNote message={error} />
      {isApp ? null : (
        <div className="page-scene mb-8">
          <ScenePhoto src={ILLUSTRATIONS.schedule} />
        </div>
      )}

      <div className="mb-8">
        <AudioPlayer clip={audio} onLoad={loadAudio} />
      </div>

      {isApp ? (
        <DoseMatrix medicines={scheduled} slotTimes={plan.slotTimes} />
      ) : (
        <div className="overflow-x-auto overflow-hidden rounded-[28px] border border-card">
          <table className="w-full text-left">
            <thead className="bg-card">
              <tr>
                <th className="px-5 py-4 font-semibold">
                  <Bilingual k="medicine" lang={uiLang} stacked />
                </th>
                {SLOTS.map((slot) => (
                  <th key={slot} className="px-5 py-4 text-center font-semibold">
                    <Bilingual k={slot} lang={uiLang} stacked />
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
                      <PlateMark relation={medicine.foodRelation} />{" "}
                      <Bilingual k={foodKey(medicine.foodRelation)} lang={uiLang} />
                    </p>
                  </th>
                  {SLOTS.map((slot) => {
                    const on = medicine.slots.includes(slot);
                    return (
                      <td key={slot} className="px-5 py-4 text-center">
                        <span className="take-skip">
                          <span className={`take-skip-dot ${on ? "is-take" : "is-skip"}`} />
                          <Bilingual k={on ? "take" : "skip"} lang={uiLang} />
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className={`mt-8 grid gap-5 ${isApp ? "" : "md:grid-cols-3"}`}>
        {doses.map((dose) => {
          const names = dose.medicineLineIds
            .map((id) => brandLabel(plan.medicines.find((medicine) => medicine.lineId === id)?.brand ?? null))
            .join(", ");
          const given = dose.status === "given";
          const missed = dose.status === "missed";
          const queued = queuedDoseIds.includes(dose.doseId);
          const statusKey: CopyKey = queued ? "queued" : given ? "given" : missed ? "missed" : "due";
          return (
            <article key={dose.doseId} className="app-panel rounded-3xl bg-card p-6">
              <div className="flex flex-col gap-2">
                <h2 className={isApp ? "font-display text-[22px] leading-snug" : "font-display text-[28px]"}>
                  {COPY[dose.slot][uiLang]} · {plan.slotTimes[dose.slot]}
                </h2>
                <StatusChip
                  icon={given ? "✓" : missed ? "✕" : "○"}
                  label={bi(statusKey, uiLang)}
                  tone={given ? "ok" : missed ? "danger" : "neutral"}
                />
              </div>
              <p className="mt-3">{names}</p>
              {!given ? (
                <div className="mt-5">
                  <Button onClick={() => markGiven(dose.doseId)}>
                    <Bilingual k="given" lang={uiLang} />
                  </Button>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      {prn.length > 0 ? (
        <section className="mt-10">
          <h2 className={isApp ? "font-display text-[22px] leading-snug" : "font-display text-[32px]"}>
            <Bilingual k="onlyWhenNeeded" lang={uiLang} />
          </h2>
          <ul className={`mt-4 grid gap-4 ${isApp ? "" : "md:grid-cols-2"}`}>
            {prn.map((medicine) => (
              <li key={medicine.lineId} className="app-panel rounded-3xl bg-card p-6">
                <p className="font-semibold">{brandLabel(medicine.brand)}</p>
                <p className="muted mt-1">{medicine.prnCondition ?? bi("notWritten", uiLang)}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
