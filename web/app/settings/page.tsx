"use client";

import { Button } from "@/components/Button";
import { PageHeader } from "@/components/PageHeader";
import { DISCLAIMER } from "@/lib/copy";
import { useDemo } from "@/lib/demo/store";

export default function SettingsPage() {
  const { reset, plan } = useDemo();

  return (
    <section>
      <PageHeader
        eyebrow="Settings"
        title="Privacy and this device"
        description="This demo stores the current plan in the browser only."
        actions={
          <Button variant="danger" onClick={reset}>
            Delete data on this device
          </Button>
        }
      />

      <div className="grid gap-5 md:grid-cols-2">
        <article className="rounded-3xl bg-card p-6">
          <h2 className="font-semibold">Safety</h2>
          <p className="mt-2">{DISCLAIMER}</p>
        </article>
        <article className="rounded-3xl bg-card p-6">
          <h2 className="font-semibold">Current plan</h2>
          <p className="mt-2 text-secondary">
            {plan ? `Plan ${plan.planId} · ${plan.status}` : "No plan on this device."}
          </p>
        </article>
      </div>
    </section>
  );
}
