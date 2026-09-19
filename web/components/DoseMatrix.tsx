"use client";

import { Bilingual } from "@/components/Bilingual";
import { PlateMark } from "@/components/PlateMark";
import { useApp } from "@/lib/app/store";
import type { FoodRelation, Slot } from "@/lib/api/types";
import { brandLabel, durationLabel, foodKey } from "@/lib/format";

const SLOTS: Slot[] = ["morning", "noon", "night", "bedtime"];

export type DoseMatrixMedicine = {
  lineId: string;
  brand: string | null;
  foodRelation: FoodRelation;
  slots: Slot[];
  durationDays?: number | null;
};

export function DoseMatrix({
  medicines,
  slotTimes,
}: {
  medicines: DoseMatrixMedicine[];
  slotTimes?: Partial<Record<Slot, string>>;
}) {
  const { uiLang } = useApp();

  return (
    <ul className="dose-matrix">
      {medicines.map((medicine) => (
        <li key={medicine.lineId} className="dose-matrix-card">
          <p className="dose-matrix-name">{brandLabel(medicine.brand)}</p>
          <p className="dose-matrix-food">
            <PlateMark relation={medicine.foodRelation} />
            <Bilingual k={foodKey(medicine.foodRelation)} lang={uiLang} />
          </p>
          {medicine.durationDays !== undefined ? (
            <p className="dose-matrix-food">{durationLabel(medicine.durationDays, uiLang)}</p>
          ) : null}
          <ul className="dose-matrix-slots">
            {SLOTS.map((slot) => {
              const on = medicine.slots.includes(slot);
              return (
                <li key={slot}>
                  <span>
                    <Bilingual k={slot} lang={uiLang} />
                    {slotTimes?.[slot] ? ` · ${slotTimes[slot]}` : ""}
                  </span>
                  <span className="take-skip">
                    <span className={`take-skip-dot ${on ? "is-take" : "is-skip"}`} />
                    <Bilingual k={on ? "take" : "skip"} lang={uiLang} />
                  </span>
                </li>
              );
            })}
          </ul>
        </li>
      ))}
    </ul>
  );
}
