import type { Plan, Slot } from "@/lib/api/types";
import { DISCLAIMER, SLOT_LABELS } from "@/lib/copy";
import { brandLabel, foodLabel } from "@/lib/format";

const SLOTS: Slot[] = ["morning", "noon", "night", "bedtime"];

export async function renderFridgePng(plan: Plan): Promise<Blob> {
  const scheduled = plan.medicines.filter((medicine) => !medicine.prn);
  const prn = plan.medicines.filter((medicine) => medicine.prn);
  const rowH = 64;
  const headerH = 140;
  const width = 1200;
  const height = Math.max(800, headerH + 80 + scheduled.length * rowH + (prn.length ? 80 + prn.length * 36 : 0) + 120);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not draw the fridge sheet.");

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = "#000000";
  ctx.font = "700 42px Helvetica, Arial, sans-serif";
  ctx.fillText("AfterCare schedule", 48, 64);
  ctx.font = "24px Helvetica, Arial, sans-serif";
  ctx.fillText(DISCLAIMER, 48, 104);

  const colW = (width - 96 - 280) / 4;
  ctx.font = "700 22px Helvetica, Arial, sans-serif";
  ctx.fillText("Medicine", 48, headerH);
  SLOTS.forEach((slot, index) => {
    const x = 328 + index * colW;
    ctx.fillText(SLOT_LABELS[slot].en, x, headerH);
    ctx.font = "18px Helvetica, Arial, sans-serif";
    ctx.fillText(plan.slotTimes[slot], x, headerH + 26);
    ctx.font = "700 22px Helvetica, Arial, sans-serif";
  });

  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(48, headerH + 40);
  ctx.lineTo(width - 48, headerH + 40);
  ctx.stroke();

  scheduled.forEach((medicine, row) => {
    const y = headerH + 80 + row * rowH;
    ctx.font = "700 22px Helvetica, Arial, sans-serif";
    ctx.fillText(brandLabel(medicine.brand), 48, y);
    ctx.font = "18px Helvetica, Arial, sans-serif";
    ctx.fillText(foodLabel(medicine.foodRelation), 48, y + 24);
    SLOTS.forEach((slot, index) => {
      const take = medicine.slots.includes(slot);
      const x = 328 + index * colW;
      ctx.beginPath();
      ctx.arc(x + 10, y - 6, 10, 0, Math.PI * 2);
      if (take) ctx.fill();
      else ctx.stroke();
      ctx.font = "18px Helvetica, Arial, sans-serif";
      ctx.fillText(take ? "Take" : "Skip", x + 28, y);
    });
  });

  if (prn.length > 0) {
    let y = headerH + 80 + scheduled.length * rowH + 36;
    ctx.font = "700 24px Helvetica, Arial, sans-serif";
    ctx.fillText("Only when needed", 48, y);
    prn.forEach((medicine) => {
      y += 36;
      ctx.font = "20px Helvetica, Arial, sans-serif";
      ctx.fillText(
        `${brandLabel(medicine.brand)} — ${medicine.prnCondition ?? "Not written, ask your doctor"}`,
        48,
        y,
      );
    });
  }

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error("Could not export the fridge sheet."));
    }, "image/png");
  });
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function shareFridgePng(blob: Blob): Promise<boolean> {
  const file = new File([blob], "aftercare-fridge-sheet.png", { type: "image/png" });
  const nav = navigator as Navigator & {
    canShare?: (data: { files: File[] }) => boolean;
    share?: (data: { files: File[]; title: string; text: string }) => Promise<void>;
  };
  if (nav.canShare?.({ files: [file] }) && nav.share) {
    await nav.share({ files: [file], title: "AfterCare fridge sheet", text: DISCLAIMER });
    return true;
  }
  return false;
}
