/* Data loader. The PWA reads plain JSON emitted by the Python brain (GitHub-as-DB,
   mirroring agentec/hypertrophy). DATA_BASE can point at a relative ./data folder
   (bundled deploy) or a raw GitHub data-repo URL (two-way sync, phase 2). Offline-first:
   responses are cached in memory + localStorage so the app opens instantly and survives
   a flaky network — same offline-first posture as the finance/hypertrophy apps. */
(function () {
  const DATA_BASE = (window.UAE_DATA_BASE || "data").replace(/\/$/, "");
  const mem = {};

  async function load(path, { cacheKey } = {}) {
    if (mem[path]) return mem[path];
    const url = `${DATA_BASE}/${path}`;
    try {
      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) throw new Error(`${res.status} ${path}`);
      const json = await res.json();
      mem[path] = json;
      if (cacheKey) try { localStorage.setItem("uae_cache_" + cacheKey, JSON.stringify(json)); } catch (e) {}
      return json;
    } catch (e) {
      // offline fallback to last good cache
      if (cacheKey) {
        const c = localStorage.getItem("uae_cache_" + cacheKey);
        if (c) { console.warn("[data] using cached", path, e.message); return JSON.parse(c); }
      }
      throw e;
    }
  }

  const DATA = {
    base: DATA_BASE,
    meta: () => load("meta.json", { cacheKey: "meta" }),
    universe: () => load("universe.json", { cacheKey: "universe" }),
    indices: () => load("indices.json", { cacheKey: "indices" }),
    events: () => load("events.json", { cacheKey: "events" }),
    commodities: () => load("commodities.json", { cacheKey: "commodities" }),
    globalEvents: () => load("global_events.json", { cacheKey: "gevents" }),
    readiness: () => load("launch_readiness.json", { cacheKey: "readiness" }),
    stock: (sym) => load(`stocks/${sym}.json`, { cacheKey: "stock_" + sym }),
  };
  window.DATA = DATA;

  /* Watchlist + alerts persistence (localStorage; phase 2 syncs to a GitHub data repo). */
  const WATCH_KEY = "uae_watchlist";
  window.Watch = {
    list() { try { return JSON.parse(localStorage.getItem(WATCH_KEY) || "[]"); } catch (e) { return []; } },
    has(sym) { return this.list().includes(sym); },
    toggle(sym) {
      const l = this.list();
      const i = l.indexOf(sym);
      if (i >= 0) l.splice(i, 1); else l.push(sym);
      localStorage.setItem(WATCH_KEY, JSON.stringify(l));
      window.dispatchEvent(new CustomEvent("watchchange"));
      return this.has(sym);
    },
  };
})();
