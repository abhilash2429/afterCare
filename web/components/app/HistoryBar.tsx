"use client";

import { useApp } from "@/lib/app/store";
import { useAppHistory } from "@/lib/app/history";
import { COPY } from "@/lib/copy";

export function HistoryBar() {
  const { uiLang } = useApp();
  const { canBack, canForward, back, forward } = useAppHistory();

  return (
    <div className="appv-hist">
      <button type="button" onClick={back} disabled={!canBack} aria-label={COPY.back[uiLang]}>
        <HistChevron dir="back" />
      </button>
      <button type="button" onClick={forward} disabled={!canForward} aria-label={COPY.forward[uiLang]}>
        <HistChevron dir="forward" />
      </button>
    </div>
  );
}

function HistChevron({ dir }: { dir: "back" | "forward" }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      {dir === "back" ? (
        <path
          d="M15 5.2 8.2 12 15 18.8"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.15"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : (
        <path
          d="M9 5.2 15.8 12 9 18.8"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.15"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </svg>
  );
}
