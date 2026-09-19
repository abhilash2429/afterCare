export type QueuedGiven = {
  doseId: string;
  queuedAt: string;
};

const KEY = "aftercare-given-queue";

export function loadQueue(): QueuedGiven[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    return JSON.parse(raw) as QueuedGiven[];
  } catch {
    return [];
  }
}

function saveQueue(items: QueuedGiven[]) {
  window.localStorage.setItem(KEY, JSON.stringify(items));
}

export function enqueueGiven(doseId: string): QueuedGiven[] {
  const items = loadQueue();
  if (items.some((item) => item.doseId === doseId)) return items;
  const next = [...items, { doseId, queuedAt: new Date().toISOString() }];
  saveQueue(next);
  return next;
}

export function dequeueGiven(doseId: string): QueuedGiven[] {
  const next = loadQueue().filter((item) => item.doseId !== doseId);
  saveQueue(next);
  return next;
}

export function clearQueue(): void {
  saveQueue([]);
}
