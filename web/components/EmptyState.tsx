"use client";

import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Button } from "@/components/Button";

export function EmptyState({
  title,
  body,
  action,
  href,
  illustration,
}: {
  title: string;
  body: string;
  action: string;
  href: string;
  illustration?: ReactNode;
}) {
  const router = useRouter();

  return (
    <section className="flex min-h-[40vh] flex-col justify-center gap-4">
      {illustration ? <div className="page-scene page-scene-center">{illustration}</div> : null}
      <h1 className="font-display text-[40px] tracking-[-0.03em]">{title}</h1>
      <p className="muted max-w-xl">{body}</p>
      <div>
        <Button onClick={() => router.push(href)}>{action}</Button>
      </div>
    </section>
  );
}
