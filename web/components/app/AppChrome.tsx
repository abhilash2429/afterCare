"use client";

import Link from "next/link";
import { HistoryBar } from "@/components/app/HistoryBar";
import { useApp } from "@/lib/app/store";
import { COPY, scriptClass } from "@/lib/copy";

export function AppChrome() {
  const { demo, uiLang } = useApp();

  return (
    <header className="appv-brand-row">
      <HistoryBar />
      <Link href="/app/" className="appv-brand-name" aria-label="AfterCare">
        AfterCare
      </Link>
      <span className="appv-spacer" />
      {demo ? <span className="demo-chip">Demo</span> : null}
      <Link href="/settings/" className={`appv-icon-btn appv-icon-btn-wide ${scriptClass(uiLang)}`}>
        {COPY.settings[uiLang]}
      </Link>
    </header>
  );
}
