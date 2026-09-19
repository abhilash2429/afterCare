import type { Crop } from "@/lib/api/types";

export function pageFromCrop(crop: Crop | null): number | null {
  if (!crop?.s3Key) return null;
  const match = crop.s3Key.match(/p(\d+)\.[a-z0-9]+$/i);
  if (!match) return null;
  return Number(match[1]);
}

export function cropBackground(crop: Crop): { backgroundSize: string; backgroundPosition: string } {
  const w = crop.w > 0 ? crop.w : 1;
  const h = crop.h > 0 ? crop.h : 1;
  const posX = w >= 1 ? "0%" : `${(crop.x / (1 - w)) * 100}%`;
  const posY = h >= 1 ? "0%" : `${(crop.y / (1 - h)) * 100}%`;
  return {
    backgroundSize: `${(1 / w) * 100}% ${(1 / h) * 100}%`,
    backgroundPosition: `${posX} ${posY}`,
  };
}
