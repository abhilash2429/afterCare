"use client";

import type { Crop } from "@/lib/api/types";
import { cropBackground, pageFromCrop } from "@/lib/media/crop";
import type { PageFile } from "@/lib/app/store";

export function SourceCrop({
  crop,
  pages,
}: {
  crop: Crop | null;
  pages: PageFile[];
}) {
  if (!crop || pages.length === 0) return null;
  const pageNumber = pageFromCrop(crop) ?? (pages.length === 1 ? 1 : null);
  if (!pageNumber) return null;
  const page = pages[pageNumber - 1];
  if (!page) return null;
  const bg = cropBackground(crop);
  return (
    <div
      role="img"
      aria-label={`Source on page ${pageNumber}`}
      className="source-crop"
      style={{
        backgroundImage: `url(${page.previewUrl})`,
        backgroundRepeat: "no-repeat",
        backgroundSize: bg.backgroundSize,
        backgroundPosition: bg.backgroundPosition,
      }}
    />
  );
}
