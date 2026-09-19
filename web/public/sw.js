const STATIC_CACHE = "aftercare-static-v2";
const PLAN_CACHE = "aftercare-plans-v2";
const ASSET_CACHE = "aftercare-assets-v2";
const KNOWN_CACHES = [STATIC_CACHE, PLAN_CACHE, ASSET_CACHE];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) =>
      cache.addAll([
        "/",
        "/schedule/",
        "/box-check/",
        "/red-flags/",
        "/family/",
        "/fridge-sheet/",
        "/settings/",
        "/icon-192.png",
        "/icon-512.png",
      ]),
    ),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) => Promise.all(names.filter((name) => !KNOWN_CACHES.includes(name)).map((name) => caches.delete(name))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "CACHE_SCHEDULE") {
    event.waitUntil(caches.open(STATIC_CACHE).then((cache) => cache.add("/schedule/")));
  }
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  // Dev chunk URLs are not content-hashed; caching them serves stale code on localhost.
  if (request.method !== "GET" || self.location.hostname === "localhost") return;
  const url = new URL(request.url);

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, STATIC_CACHE));
    return;
  }
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(cacheFirst(request, ASSET_CACHE));
    return;
  }
  if (url.pathname.includes("/plans/")) {
    event.respondWith(networkFirst(request, PLAN_CACHE));
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

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}
