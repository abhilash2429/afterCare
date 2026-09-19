"use client";

import { useEffect } from "react";
import { registerServiceWorker } from "@/lib/push/register";

export function ServiceWorkerRegister() {
  useEffect(() => {
    void registerServiceWorker();
  }, []);
  return null;
}
