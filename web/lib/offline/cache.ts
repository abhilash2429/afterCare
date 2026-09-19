const PLAN_KEY = "aftercare-plan-cache";
const DOSES_KEY = "aftercare-doses-cache";

export function cachePlanJson(json: string): void {
  window.localStorage.setItem(PLAN_KEY, json);
}

export function cacheDosesJson(json: string): void {
  window.localStorage.setItem(DOSES_KEY, json);
}

export function loadCachedPlanJson(): string | null {
  return window.localStorage.getItem(PLAN_KEY);
}

export function loadCachedDosesJson(): string | null {
  return window.localStorage.getItem(DOSES_KEY);
}

export function clearCaches(): void {
  window.localStorage.removeItem(PLAN_KEY);
  window.localStorage.removeItem(DOSES_KEY);
}

export function notifyWorkerToCachePlan(): void {
  if (!("serviceWorker" in navigator)) return;
  navigator.serviceWorker.controller?.postMessage({ type: "CACHE_SCHEDULE" });
}
