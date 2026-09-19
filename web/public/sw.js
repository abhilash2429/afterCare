self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open("aftercare-static-v1").then((cache) =>
      cache.addAll(["/schedule/", "/box-check/", "/red-flags/", "/icon-192.png", "/icon-512.png"]),
    ),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "CACHE_SCHEDULE") {
    event.waitUntil(caches.open("aftercare-static-v1").then((cache) => cache.add("/schedule/")));
  }
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.pathname.includes("/plans/")) {
    event.respondWith(networkFirst(request, "aftercare-plans-v1"));
  }
});

self.addEventListener("push", (event) => {
  let title = "AfterCare";
  let body = "Time for the next dose.";
  try {
    const data = event.data ? event.data.json() : null;
    if (data && typeof data.title === "string") title = data.title;
    if (data && typeof data.body === "string") body = data.body;
  } catch {
    // Keep the default title and body.
  }
  event.waitUntil(self.registration.showNotification(title, { body, data: { url: "/schedule/" } }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/schedule/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((client) => "focus" in client);
      if (existing) {
        existing.navigate(url);
        return existing.focus();
      }
      return self.clients.openWindow(url);
    }),
  );
});

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw new Error("offline");
  }
}
