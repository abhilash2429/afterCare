"use client";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusChip } from "@/components/StatusChip";
import { bi } from "@/lib/copy";
import { useApp } from "@/lib/app/store";

export default function RedFlagsPage() {
  const { ready, plan, uiLang } = useApp();

  if (!ready) return <p>{bi("loading", uiLang)}</p>;
  if (!plan) {
    return (
      <EmptyState
        title="noWarnings"
        body="noWarningsBody"
        action="photographPaper"
        href="/upload/"
      />
    );
  }

  const flags = plan.redFlags;
  const fromDocument = flags.source === "document";

  return (
    <section>
      <PageHeader eyebrow="redFlags" title="watchSigns" description="redFlagsDesc" />

      <article className={`app-panel rounded-3xl p-8 ${fromDocument ? "bg-danger-soft" : "bg-warn-soft"}`}>
        {fromDocument ? (
          <StatusChip icon="📄" label={bi("fromDocument", uiLang)} tone="danger" />
        ) : (
          <StatusChip icon="ℹ" label={bi("genericBand", uiLang)} tone="warn" />
        )}
        <p className="mt-5 text-[18px] leading-snug">{flags.text}</p>
      </article>
    </section>
  );
}
