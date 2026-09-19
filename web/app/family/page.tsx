"use client";

import { Bilingual } from "@/components/Bilingual";
import { DoseMatrix } from "@/components/DoseMatrix";
import { EmptyState } from "@/components/EmptyState";
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

export default function FamilyPage() {
  const { ready, plan, weekDoses, givenPct, uiLang } = useApp();
  const { isApp } = useAppView();

  if (!ready) return <p>{bi("loading", uiLang)}</p>;
  if (!plan || plan.status !== "active") {
    return (
      <EmptyState
        title="noScheduleWatch"
        body="noScheduleWatchBody"
        action="openSchedule"
        href="/schedule/"
        illustration={<ScenePhoto src={ILLUSTRATIONS.schedule} />}
      />
    );
  }

  const scheduled = plan.medicines.filter((medicine) => !medicine.prn);
  const byDate = new Map<string, typeof weekDoses>();
  for (const dose of weekDoses) {
    const list = byDate.get(dose.date) ?? [];
    list.push(dose);
    byDate.set(dose.date, list);
  }
  const days = [...byDate.keys()].sort((a, b) => b.localeCompare(a));
  const description =
    givenPct === null ? "readOnlyFamily" : `${givenPct}% ${COPY.givenPctLine[uiLang]}`;

  return (
    <section>
      <PageHeader eyebrow="familyView" title="howWeekGoing" description={description} />

      {isApp ? (
        <DoseMatrix medicines={scheduled} />
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
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scheduled.map((medicine) => (
                <tr key={medicine.lineId} className="border-t border-card">
                  <th className="px-5 py-4">
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

      <ul className="mt-8 grid gap-4">
        {days.map((date) => {
          const doses = byDate.get(date) ?? [];
          const given = doses.filter((dose) => dose.status === "given").length;
          return (
            <li key={date} className="app-panel rounded-3xl bg-card p-6">
              <div className="flex flex-col gap-2">
                <h2 className={isApp ? "font-display text-[22px] leading-snug" : "font-display text-[28px]"}>{date}</h2>
                <StatusChip icon="%" label={`${given} / ${doses.length} ${bi("ofGiven", uiLang)}`} tone="ok" />
              </div>
              <ul className="mt-4 grid gap-2">
                {doses.map((dose) => {
                  const statusKey: CopyKey =
                    dose.status === "given" ? "given" : dose.status === "missed" ? "missed" : "pending";
                  return (
                    <li key={dose.doseId}>
                      {bi(dose.slot, uiLang)} — {bi(statusKey, uiLang)}
                    </li>
                  );
                })}
              </ul>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
