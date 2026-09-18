"use client";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusChip } from "@/components/StatusChip";
import { GENERIC_RED_FLAGS } from "@/lib/demo/fixtures";
import { useDemo } from "@/lib/demo/store";

export default function RedFlagsPage() {
  const { ready, plan } = useDemo();

  if (!ready) return <p>Loading red flags…</p>;
  if (!plan) {
    return (
      <EmptyState
        title="No warnings yet"
        body="Photograph a discharge summary to load the red-flag card."
        action="Photograph paper"
        href="/upload/"
      />
    );
  }

  const flags = plan.redFlags;
  const fromDocument = flags.source === "document";

  return (
    <section>
      <PageHeader
        eyebrow="Red flags"
        title="Watch for these signs"
        description="Warnings from the document stay verbatim. Generic advice is labelled separately."
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <article className="rounded-3xl bg-danger-soft p-8">
          {fromDocument ? (
            <StatusChip icon="📄" label="From your document" tone="danger" />
          ) : (
            <StatusChip icon="ℹ" label="General advice. Not from your document." tone="warn" />
          )}
          <p className="mt-5 text-[22px] leading-snug">{flags.text}</p>
        </article>

        {fromDocument ? (
          <article className="rounded-3xl bg-card p-8">
            <StatusChip icon="ℹ" label="General advice. Not from your document." tone="warn" />
            <p className="mt-5 text-[20px] leading-snug">{GENERIC_RED_FLAGS.text}</p>
          </article>
        ) : null}
      </div>
    </section>
  );
}
