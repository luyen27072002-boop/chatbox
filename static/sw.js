const CACHE = "oday-platform-static-v23";
const STATIC_ASSETS = [
  "/",
  "/static/styles.css",
  "/static/app.js",
  "/static/platform.css",
  "/static/platform.js",
  "/static/home.css",
  "/static/home.js",
  "/static/language/style.css",
  "/static/language/app.js",
  "/static/manifest.json",
  "/static/icons/brand-logo.png",
  "/static/icons/favicon.ico",
  "/static/icons/favicon-16x16.png",
  "/static/icons/favicon-32x32.png",
  "/static/icons/favicon-48x48.png",
  "/static/icons/apple-touch-icon.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/icon-maskable-192.png",
  "/static/icons/icon-maskable-512.png"
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(STATIC_ASSETS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    Promise.all([
      caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))),
      self.clients.claim(),
    ])
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET" || event.request.url.includes("/api/")) return;
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
