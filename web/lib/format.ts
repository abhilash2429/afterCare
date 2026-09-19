import type { FoodRelation, Medicine, Molecule, SlotTimes } from "@/lib/api/types";
import { COPY, NOT_WRITTEN, SLOT_LABELS, type CopyKey, type UiLang } from "@/lib/copy";

export function todayIst(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

export function moleculeLabel(molecule: Molecule): string {
  const unit = molecule.unit ?? "mg";
  if (molecule.strengthMg === null) {
    return `${molecule.name} — ${NOT_WRITTEN}`;
  }
  return `${molecule.name} ${molecule.strengthMg} ${unit}`;
}

export function medicineMolecules(medicine: Medicine): string {
  if (medicine.molecules.length === 0) {
    return NOT_WRITTEN;
  }
  return medicine.molecules.map(moleculeLabel).join(" + ");
}

export function durationLabel(days: number | null, language: UiLang = "en"): string {
  if (days === null) {
    return COPY.durationUnknown[language];
  }
  return `${days} ${COPY.days[language]}`;
}

export function foodKey(relation: FoodRelation): CopyKey {
  if (relation === "before") return "beforeFood";
  if (relation === "after") return "afterFood";
  return "notWritten";
}

export function foodLabel(relation: FoodRelation, language: UiLang = "en"): string {
  return COPY[foodKey(relation)][language];
}

export function frequencyLabel(frequency: string | null, language: UiLang = "en"): string {
  if (frequency === null) return COPY.notWritten[language];
  return frequency;
}

export function brandLabel(brand: string | null, language: UiLang = "en"): string {
  return brand ?? COPY.notWritten[language];
}

export function slotTime(times: SlotTimes, slot: keyof SlotTimes): string {
  return times[slot];
}

export function slotTitle(slot: keyof typeof SLOT_LABELS, language: UiLang = "en"): string {
  return SLOT_LABELS[slot][language];
}

export function writtenOrAsk(value: string | null | undefined, language: UiLang = "en"): string {
  if (!value) return COPY.notWritten[language];
  return value;
}
