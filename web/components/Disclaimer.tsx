"use client";

import { CopyLine } from "@/components/Bilingual";
import { useApp } from "@/lib/app/store";

export function Disclaimer() {
  const { uiLang } = useApp();
  return (
    <p className="text-center text-[16px] leading-snug">
      <CopyLine k="disclaimer" lang={uiLang} as="span" />
    </p>
  );
}
