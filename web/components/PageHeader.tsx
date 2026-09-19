"use client";

import type { ReactNode } from "react";
import { CopyLine } from "@/components/Bilingual";
import { useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";
import type { CopyKey } from "@/lib/copy";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: CopyKey;
  title: CopyKey;
  description?: CopyKey | string;
  actions?: ReactNode;
}) {
  const { uiLang } = useApp();
  const { isApp } = useAppView();

  return (
    <div className={isApp ? "appv-page-head" : "mb-10 flex flex-wrap items-end justify-between gap-6"}>
      <div className={isApp ? undefined : "max-w-2xl"}>
        <CopyLine k={eyebrow} lang={uiLang} className="landing-eyebrow mb-3" regionalClassName="muted mt-1" />
        <CopyLine
          k={title}
          lang={uiLang}
          as="h1"
          className={
            isApp
              ? "font-display mt-1 text-[28px] leading-[1.15] tracking-[-0.03em] text-primary"
              : "font-display mt-3 text-[44px] leading-[1.1] tracking-[-0.03em] text-primary"
          }
          regionalClassName={isApp ? "muted mt-1 text-[16px]" : "muted mt-2 text-[22px]"}
        />
        {description ? (
          <CopyLine
            k={description}
            lang={uiLang}
            className={isApp ? "appv-page-desc mt-2 text-[15px] leading-snug text-primary/75" : "mt-3 text-primary/75"}
            regionalClassName="muted mt-1"
          />
        ) : null}
      </div>
      {actions ? <div className={isApp ? "appv-page-actions" : "flex flex-wrap gap-3"}>{actions}</div> : null}
    </div>
  );
}
