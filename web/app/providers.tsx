"use client";

import { AppProvider } from "@/lib/app/store";
import { AppViewProvider } from "@/lib/app/view";
import { AppHistoryProvider } from "@/lib/app/history";
import { AppShell } from "@/components/AppShell";
import { ServiceWorkerRegister } from "@/components/ServiceWorkerRegister";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AppProvider>
      <AppViewProvider>
        <AppHistoryProvider>
          <ServiceWorkerRegister />
          <AppShell>{children}</AppShell>
        </AppHistoryProvider>
      </AppViewProvider>
    </AppProvider>
  );
}
