/* Service worker — offline-first app shell (mirrors the agentec/hypertrophy PWAs).
   Shell is cache-first; data is network-first with a cache fallback so the app opens
   instantly and survives a flaky connection, but still pulls fresh JSON when online. */
const SHELL = "uae-shell-v1";
const DATA = "uae-data-v1";
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
    e.respondWith(
      fetch(e.request).then((res) => {
        const copy = res.clone();
        caches.open(DATA).then((c) => c.put(e.request, copy));
        return res;
      }).catch(() => caches.match(e.request))
    );
  } else {
    e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
  }
});
