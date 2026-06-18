/* Service worker — offline-capable but UPDATE-FRIENDLY.
   The shell is stale-while-revalidate: serve from cache instantly, then refetch in the
   background so the next load is fresh (fixes the old cache-first-forever bug where users
   were stuck on stale JS after a deploy). Data is network-first. The cache name carries a
   per-build id (refresh.sh stamps __BUILD_ID__), so each deploy cleanly supersedes the last. */
const VERSION = "__BUILD_ID__";
const SHELL = "uae-shell-" + VERSION;
const DATA = "uae-data-" + VERSION;
const SHELL_ASSETS = [
  "./", "./index.html", "./css/app.css",
  "./js/i18n.js", "./js/data.js", "./js/charts.js", "./js/app.js",
  "./manifest.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) =>
    Promise.all(keys.filter((k) => ![SHELL, DATA].includes(k)).map((k) => caches.delete(k)))
  ).then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  const isData = url.pathname.includes("/data/") && url.pathname.endsWith(".json");
  if (isData) {
    // network-first: always pull fresh JSON when online, fall back to cache offline
    e.respondWith(
      fetch(e.request).then((res) => {
        const copy = res.clone();
        caches.open(DATA).then((c) => c.put(e.request, copy));
        return res;
      }).catch(() => caches.match(e.request))
    );
  } else {
    // stale-while-revalidate: instant from cache, refresh cache in the background
    e.respondWith(
      caches.match(e.request).then((hit) => {
        const fresh = fetch(e.request).then((res) => {
          if (res && res.status === 200) caches.open(SHELL).then((c) => c.put(e.request, res.clone()));
          return res;
        }).catch(() => hit);
        return hit || fresh;
      })
    );
  }
});
