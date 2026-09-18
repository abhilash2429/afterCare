import type { FoodRelation, Medicine, Molecule, SlotTimes } from "@/lib/api/types";
import { SLOT_LABELS } from "@/lib/copy";

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
    return `${molecule.name} — strength not stated. Ask your doctor.`;
  }
  return `${molecule.name} ${molecule.strengthMg} ${unit}`;
}

export function medicineMolecules(medicine: Medicine): string {
  if (medicine.molecules.length === 0) {
    return "Molecule not stated. Ask your doctor.";
  }
  return medicine.molecules.map(moleculeLabel).join(" + ");
}

export function durationLabel(days: number | null): string {
  if (days === null) {
    return "Duration not stated. Ask your doctor.";
  }
  return `${days} days`;
}

export function foodLabel(relation: FoodRelation): string {
  if (relation === "before") return "Before food";
  if (relation === "after") return "After food";
  return "Food relation not stated";
}

export function frequencyLabel(frequency: string | null): string {
  if (frequency === null) {
    return "Frequency not stated. Ask your doctor.";
  }
  return frequency;
}

export function brandLabel(brand: string | null): string {
  return brand ?? "Brand not stated";
}

export function slotTime(times: SlotTimes, slot: keyof SlotTimes): string {
  return times[slot];
}

export function slotTitle(slot: keyof typeof SLOT_LABELS): string {
  return `${SLOT_LABELS[slot].en} · ${SLOT_LABELS[slot].kn}`;
}
