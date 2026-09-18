"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/Button";
import { PageHeader } from "@/components/PageHeader";
import { setSession } from "@/lib/auth/session";

export default function JoinPage() {
  return (
    <Suspense fallback={<p>Opening invite…</p>}>
      <JoinInner />
    </Suspense>
  );
}

function JoinInner() {
  const params = useSearchParams();
  const circleId = params.get("c");
  const token = params.get("t");
  const [joined, setJoined] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!circleId || !token) {
      setError("This invite link is missing a circle or token. Ask the family owner for a new link.");
    }
  }, [circleId, token]);

  function join() {
    if (!circleId || !token) return;
    setSession({
      token: "demo-caregiver-session",
      role: "caregiver",
      circleId,
    });
    setJoined(true);
  }

  return (
    <section>
      <PageHeader
        eyebrow="Care circle"
        title="Join this care circle"
        description="A caregiver can view the schedule, mark Given, and run Box Check. They cannot edit the plan."
        actions={
          <Button onClick={join} disabled={!circleId || !token || joined}>
            Join as caregiver
          </Button>
        }
      />
      {error ? <p className="rounded-3xl bg-danger-soft p-6 text-danger">{error}</p> : null}
      {joined ? (
        <p className="rounded-3xl bg-ok-soft p-6 text-ok">Joined as caregiver on this browser.</p>
      ) : null}
    </section>
  );
}
