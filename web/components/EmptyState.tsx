"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Button } from "@/components/Button";
import { CopyLine } from "@/components/Bilingual";
import { useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";
import { bi, type CopyKey } from "@/lib/copy";

export function EmptyState({
  title,
  body,
  action,
  href,
  illustration,
}: {
  title: CopyKey;
  body: CopyKey;
  action: CopyKey;
  href: string;
  illustration?: ReactNode;
}) {
  const router = useRouter();
  const { uiLang } = useApp();
  const { isApp } = useAppView();

  return (
    <section className={`flex flex-col justify-center gap-4 ${isApp ? "min-h-0 py-4" : "min-h-[40vh]"}`}>
      {illustration ? <div className="page-scene page-scene-center">{illustration}</div> : null}
      <CopyLine
        k={title}
        lang={uiLang}
        as="h1"
        className={isApp ? "font-display text-[28px] tracking-[-0.03em]" : "font-display text-[40px] tracking-[-0.03em]"}
        regionalClassName={isApp ? "muted text-[16px]" : "muted text-[22px]"}
      />
      <CopyLine k={body} lang={uiLang} className={isApp ? "muted text-[15px]" : "muted max-w-xl"} />
      <div>
        <Button onClick={() => router.push(href)}>{bi(action, uiLang)}</Button>
      </div>
    </section>
  );
}
