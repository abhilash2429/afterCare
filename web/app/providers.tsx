"use client";

import { DemoProvider } from "@/lib/demo/store";
import { AppShell } from "@/components/AppShell";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <DemoProvider>
      <AppShell>{children}</AppShell>
    </DemoProvider>
  );
}
