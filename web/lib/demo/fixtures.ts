import type { BoxCheckItem, Dose, Medicine, Plan, Slot } from "@/lib/api/types";
import { GENERIC_RED_FLAG } from "@/lib/copy";
import { todayIst } from "@/lib/format";

const CIRCLE_ID = "ci_demo_hubli";
const PLAN_ID = "pl_case01";
const DOCUMENT_ID = "doc_case01";

function med(
  partial: Omit<Medicine, "sourceBlockIds" | "crop" | "source" | "form"> &
    Partial<Pick<Medicine, "form" | "source">>,
): Medicine {
  return {
    form: "tablet",
    source: "textract",
    crop: null,
    sourceBlockIds: [`b_${partial.lineId}`],
    ...partial,
  };
}

export const DEMO_PLAN: Plan = {
  planId: PLAN_ID,
  circleId: CIRCLE_ID,
  patientName: null,
  sourceDocumentIds: [DOCUMENT_ID],
  language: "kn",
  status: "draft",
  slotTimes: {
    morning: "08:00",
    noon: "14:00",
    night: "20:00",
    bedtime: "22:00",
  },
  followUp: {
    date: "2026-09-28",
    with: "Cardiology OPD",
    confidence: 0.9,
  },
  redFlags: {
    source: "document",
    text: "Report immediately to the emergency department if chest pain returns, breathlessness at rest, bleeding from any site, or black stools.",
    sourceBlockIds: ["b_rf1"],
  },
  medicines: [
    med({
      lineId: "m1",
      rawText: "T. Ecosprin 75 1-0-0 after food x 30 days",
      brand: "Ecosprin",
      molecules: [{ name: "aspirin", strengthMg: 75, unit: "mg" }],
      frequency: "1-0-0",
      slots: ["morning"],
      prn: false,
      prnCondition: null,
      foodRelation: "after",
      durationDays: 30,
      confidence: 0.94,
      needsConfirmation: false,
    }),
    med({
      lineId: "m2",
      rawText: "T. Clopitab 75 0-0-1 after food x 30 days",
      brand: "Clopitab",
      molecules: [{ name: "clopidogrel", strengthMg: 75, unit: "mg" }],
      frequency: "0-0-1",
      slots: ["night"],
      prn: false,
      prnCondition: null,
      foodRelation: "after",
      durationDays: 30,
      confidence: 0.93,
      needsConfirmation: false,
    }),
    med({
      lineId: "m3",
      rawText: "T. Atorva 40 HS x 30 days",
      brand: "Atorva",
      molecules: [{ name: "atorvastatin", strengthMg: 40, unit: "mg" }],
      frequency: "HS",
      slots: ["bedtime"],
      prn: false,
      prnCondition: null,
      foodRelation: "unspecified",
      durationDays: 30,
      confidence: 0.91,
      needsConfirmation: false,
    }),
    med({
      lineId: "m4",
      rawText: "Tab Pan 40 BD before food x 14 days",
      brand: "Pan",
      molecules: [{ name: "pantoprazole", strengthMg: 40, unit: "mg" }],
      frequency: "BD",
      slots: ["morning", "night"],
      prn: false,
      prnCondition: null,
      foodRelation: "before",
      durationDays: 14,
      confidence: 0.9,
      needsConfirmation: false,
    }),
    med({
      lineId: "m5",
      rawText: "T. Pantocid 40 OD before food",
      brand: "Pantocid",
      molecules: [{ name: "pantoprazole", strengthMg: 40, unit: "mg" }],
      frequency: "OD",
      slots: ["morning"],
      prn: false,
      prnCondition: null,
      foodRelation: "before",
      durationDays: null,
      confidence: 0.72,
      needsConfirmation: true,
    }),
    med({
      lineId: "m6",
      rawText: "Tab Glycomet GP1 BD after food x 30 days",
      brand: "Glycomet GP1",
      molecules: [
        { name: "metformin", strengthMg: 500, unit: "mg" },
        { name: "glimepiride", strengthMg: 1, unit: "mg" },
      ],
      frequency: "BD",
      slots: ["morning", "night"],
      prn: false,
      prnCondition: null,
      foodRelation: "after",
      durationDays: 30,
      confidence: 0.88,
      needsConfirmation: false,
    }),
    med({
      lineId: "m7",
      rawText: "T. Sorbitrate 5 SOS for chest pain",
      brand: "Sorbitrate",
      molecules: [{ name: "isosorbide dinitrate", strengthMg: 5, unit: "mg" }],
      frequency: "SOS",
      slots: [],
      prn: true,
      prnCondition: "for chest pain",
      foodRelation: "unspecified",
      durationDays: null,
      confidence: 0.89,
      needsConfirmation: false,
    }),
  ],
};

export const GENERIC_RED_FLAGS = {
  source: "generic" as const,
  text: GENERIC_RED_FLAG,
};

export const DEMO_BOX_CHECK: BoxCheckItem[] = [
  {
    verdict: "matched",
    reason: "exact_match",
    message: "This matches your prescription.",
    prescribedLineId: "m1",
    stripBrandText: "Ecosprin 75",
    stripMolecules: [{ name: "aspirin", strengthMg: 75, unit: "mg" }],
  },
  {
    verdict: "matched",
    reason: "exact_match",
    message: "This matches your prescription.",
    prescribedLineId: "m2",
    stripBrandText: "Clopitab 75",
    stripMolecules: [{ name: "clopidogrel", strengthMg: 75, unit: "mg" }],
  },
  {
    verdict: "matched",
    reason: "exact_match",
    message: "This matches your prescription.",
    prescribedLineId: "m3",
    stripBrandText: "Atorva 40",
    stripMolecules: [{ name: "atorvastatin", strengthMg: 40, unit: "mg" }],
  },
  {
    verdict: "matched",
    reason: "exact_match",
    message: "This matches your prescription.",
    prescribedLineId: "m4",
    stripBrandText: "Pan 40",
    stripMolecules: [{ name: "pantoprazole", strengthMg: 40, unit: "mg" }],
  },
  {
    verdict: "do_not_take",
    reason: "duplicate_molecule",
    message: "Two of your medicines contain the same drug. Do not take both - ask your doctor.",
    prescribedLineId: "m5",
    stripBrandText: "Pantocid 40",
    stripMolecules: [{ name: "pantoprazole", strengthMg: 40, unit: "mg" }],
  },
  {
    verdict: "matched",
    reason: "exact_match",
    message: "This matches your prescription.",
    prescribedLineId: "m6",
    stripBrandText: "Glycomet GP1",
    stripMolecules: [
      { name: "metformin", strengthMg: 500, unit: "mg" },
      { name: "glimepiride", strengthMg: 1, unit: "mg" },
    ],
  },
  {
    verdict: "check",
    reason: "strength_mismatch",
    message: "Same medicine, different strength. Check with your chemist.",
    prescribedLineId: "m1",
    stripBrandText: "Aspirin 150",
    stripMolecules: [{ name: "aspirin", strengthMg: 150, unit: "mg" }],
  },
  {
    verdict: "do_not_take",
    reason: "missing_from_box",
    message: "This medicine is not in the box. Do not skip it - ask your doctor.",
    prescribedLineId: "m7",
    stripBrandText: null,
    stripMolecules: [],
  },
];

export function dosesForPlan(plan: Plan, date = todayIst()): Dose[] {
  const slots: Slot[] = ["morning", "noon", "night", "bedtime"];
  const doses: Dose[] = [];
  for (const slot of slots) {
    const medicineLineIds = plan.medicines
      .filter((medicine) => !medicine.prn && medicine.slots.includes(slot))
      .map((medicine) => medicine.lineId);
    if (medicineLineIds.length === 0) continue;
    doses.push({
      doseId: `${plan.circleId}#${date}#${slot}`,
      date,
      slot,
      status: "pending",
      givenAt: null,
      givenBy: null,
      medicineLineIds,
    });
  }
  return doses;
}

export const EXTRACT_STEPS = [
  "Uploading pages",
  "Reading the prescription...",
  "Finding each medicine",
  "Building the schedule",
];
