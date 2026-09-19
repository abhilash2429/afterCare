"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Bilingual } from "@/components/Bilingual";
import { Button } from "@/components/Button";
import { ErrorNote } from "@/components/ErrorNote";
import { PageHeader } from "@/components/PageHeader";
import { INVITE_USED } from "@/lib/app/errors";
import { useApp } from "@/lib/app/store";
import { bi } from "@/lib/copy";

export default function JoinPage() {
  return (
    <Suspense fallback={<JoinFallback />}>
      <JoinInner />
    </Suspense>
  );
}

function JoinFallback() {
  const { uiLang } = useApp();
  return <p>{bi("loading", uiLang)}</p>;
}

const joining = new Set<string>();

function JoinInner() {
  const params = useSearchParams();
  const router = useRouter();
  const circleId = params.get("c");
  const token = params.get("t");
  const { joinInvite, error, uiLang } = useApp();
  const [joined, setJoined] = useState(false);
  const [busy, setBusy] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  useEffect(() => {
    if (!circleId || !token) {
      setLinkError("This invite link is missing a circle or token. Ask the family owner for a new link.");
      return;
    }
    const key = `${circleId}:${token}`;
    if (joining.has(key)) return;
    joining.add(key);
    setBusy(true);
    void joinInvite(circleId, token).then((ok) => {
      setBusy(false);
      if (ok) {
        setJoined(true);
        router.push("/schedule/");
      }
    });
  }, [circleId, joinInvite, router, token]);

  async function join() {
    if (!circleId || !token) return;
    setBusy(true);
    const ok = await joinInvite(circleId, token);
    setBusy(false);
    if (ok) {
      setJoined(true);
      router.push("/schedule/");
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="careCircle"
        title="joinTitle"
        description="joinDesc"
        actions={
          <Button onClick={join} disabled={!circleId || !token || joined || busy}>
            <Bilingual k="joinAsCaregiver" lang={uiLang} />
          </Button>
        }
      />
      <ErrorNote message={linkError ?? (error === INVITE_USED ? INVITE_USED : error)} />
      {joined ? (
        <p className="rounded-3xl bg-ok-soft p-6 text-ok">{bi("joinedOk", uiLang)}</p>
      ) : null}
    </section>
  );
}
