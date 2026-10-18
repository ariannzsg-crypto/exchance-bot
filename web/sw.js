/* EXCHANCE — Service Worker
   استراتژی:
     • فایل‌های استاتیک: cache-first (نسخه‌دار)
     • /api/market و /api/news و /api/history: network-first با فالبک به آخرین پاسخ کش‌شده
       (برای نمایش آخرین قیمت‌ها در حالت آفلاین)
*/
const VERSION = "ex-v5";
const STATIC_CACHE = `${VERSION}-static`;
const API_CACHE = `${VERSION}-api`;

const STATIC_ASSETS = [
  "/",
  "/index.html",
  "/config.js",
  "/app.js",
  "/design-tokens.css",
  "/manifest.json",
  "/icon.svg",
];

const CACHEABLE_API = ["/api/market", "/api/news", "/api/history", "/api/fear_greed"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (CACHEABLE_API.some((p) => url.pathname.startsWith(p))) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(API_CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request).then((hit) => hit || Response.error()))
    );
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() => caches.match("/index.html").then((hit) => hit || Response.error()))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((hit) => {
      if (hit) return hit;
      return fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
        }
        return response;
      });
    })
  );
});
