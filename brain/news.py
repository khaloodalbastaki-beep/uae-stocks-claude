"""
Live news fetcher — real, free, no key. Pulls recent media coverage per UAE-listed company
from GDELT DOC 2.0 and caches it to data/news/<SYMBOL>.json. The pipeline reads that for the
"News & Disclosures" tab so the news is REAL (live media), not mock.

GDELT hard-limits ~1 request / 5s per IP, so this is staleness-rotated (--stale N) like Mizan:
each scheduled run refreshes only the oldest N, skipping recently-touched ones, and spaces
calls ≥5s. Honest-degraded: on a rate-limit/empty result it keeps the prior cache rather than
wiping it.

    python3 -m brain.news --all            # full sweep (≥5s spacing; ~5 min for 54)
    python3 -m brain.news --stale 8        # the 8 stalest (for the hourly schedule)
    python3 -m brain.news --symbols EMAAR,FAB
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .registry import load_universe, by_symbol, Security

UTC = timezone.utc
DATA = Path(__file__).resolve().parent.parent / "data" / "news"
GNEWS = "https://news.google.com/rss/search"       # primary: reliable, free, per-company
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"  # fallback (heavily rate-limited)
UA = "Mozilla/5.0 (uae-stocks-intel news)"
MIN_INTERVAL = 6.0
_last = [time.monotonic() - MIN_INTERVAL]   # allow the first call immediately, then space


def _iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now(UTC)).replace(microsecond=0).isoformat()


def _parse_seendate(s: str) -> str:
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).replace(microsecond=0).isoformat()
    except Exception:
        return s


# UAE/Gulf/finance outlets where coverage of a named UAE listco is genuinely about it.
WHITELIST = (
    "zawya.com", "gulfnews.com", "thenationalnews.com", "khaleejtimes.com",
    "arabianbusiness.com", "wam.ae", "mubasher.info", "argaam.com", "gulfbusiness.com",
    "tradearabia.com", "meed.com", "reuters.com", "bloomberg.com", "ft.com", "cnbc.com",
    "edgemiddleeast.com", "investing.com", "marketscreener.com", "thefinanceworld.com",
    "economymiddleeast.com", "abudhabichamber.ae", "dfm.ae", "adx.ae", "cpifinancial.net",
    "menabytes.com", "wamda.com", "thepeninsulaqatar.com", "dailynewsegypt.com",
    "sahmcapital.com", "aletihad.ae", "alkhaleej.ae", "emaratalyoum.com",
)

_STOP = {"the", "and", "for", "group", "holding", "company", "co", "pjsc", "psc", "bank",
         "properties", "national", "abu", "dhabi", "dubai", "emirates", "industries",
         "international", "uae", "development", "restaurants", "insurance", "financial",
         "capital", "first", "gulf", "company", "systems", "central", "integrated"}


def _keywords(sec: Security) -> list[str]:
    toks = [sec.symbol.lower()]
    for w in sec.name_en.replace("(", " ").replace(")", " ").split():
        wl = w.lower().strip(".,&")
        if len(wl) >= 4 and wl not in _STOP:
            toks.append(wl)
    return toks


_FIN = ("profit", "revenue", "dividend", "earnings", "share", "stake", "result", "ipo",
        "rating", "stock", "loss", "acquisi", "merger", "contract", "net income", "quarter",
        "deal", "bond", "sukuk", "buyback", "guidance", "ceo", "board", "award", "expansion")


def _title_relevant(title: str, sec: Security) -> bool:
    """Keep only titles that actually name the company or carry a finance signal — drops the
    occasional tangential (e.g. geopolitics) result a broad phrase search can return."""
    tl = (title or "").lower()
    return any(k in tl for k in _keywords(sec)) or any(k in tl for k in _FIN)


def _relevant(item: dict, sec: Security) -> bool:
    dom = (item.get("domain") or "").lower()
    if any(dom.endswith(w) for w in WHITELIST):
        return True
    title = (item.get("title") or "").lower()
    return any(k in title for k in _keywords(sec))


def _query(sec: Security) -> str:
    # exact company phrase (precise) biased to financial coverage so we get relevant
    # market news, not tangential mentions. Drop legal suffixes that hurt recall.
    name = sec.name_en.split("(")[0].strip()
    return f'"{name}" (shares OR profit OR results OR dividend OR earnings OR stock OR revenue OR PJSC)'


def _fetch_google(sec: Security, limit: int = 8, days: int = 60) -> list[dict]:
    """Primary source — Google News RSS for the exact company phrase. Reliable + free +
    per-company + dated; not rate-limited like GDELT. Returns recent items (≤ `days` old)."""
    name = sec.name_en.split("(")[0].strip()
    q = (f'"{name}" (shares OR profit OR results OR dividend OR earnings OR stock OR '
         f'revenue OR stake OR contract OR IPO OR rating)')
    url = f"{GNEWS}?{urllib.parse.urlencode({'q': q, 'hl': 'en-AE', 'gl': 'AE', 'ceid': 'AE:en'})}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read().decode("utf-8", "replace"))
    cutoff = datetime.now(UTC) - timedelta(days=days)
    seen, items = set(), []
    for it in root.findall(".//item"):
        title = (it.findtext("title") or "").strip()
        src = it.find("{*}source")
        dom = ""
        if src is not None and src.get("url"):
            dom = urllib.parse.urlparse(src.get("url")).netloc.replace("www.", "")
        dt = None
        try:
            dt = parsedate_to_datetime(it.findtext("pubDate")).astimezone(UTC)
        except Exception:
            dt = None
        if dt and dt < cutoff:
            continue
        # Google News suffixes the source onto the title (" ... - Reuters") — strip it
        if dom and title.endswith(" - " + (src.text or "")):
            title = title[: -(len(src.text) + 3)].strip()
        key = (dom, title[:60].lower())
        if not title or key in seen or not _title_relevant(title, sec):
            continue
        seen.add(key)
        items.append({"title": title, "url": it.findtext("link"), "domain": dom,
                      "published_at": _iso(dt) if dt else _iso(),
                      "lang": "English", "source_type": "media"})
        if len(items) >= limit:
            break
    return items


def _fetch_gdelt(sec: Security, limit: int = 8, timespan: str = "30d") -> list[dict]:
    """Fallback — GDELT DOC 2.0. Heavily rate-limited (≈1 req/5s, frequent 429s)."""
    params = {"query": _query(sec), "mode": "ArtList", "format": "json",
              "maxrecords": str(limit * 2), "timespan": timespan, "sort": "DateDesc"}
    url = f"{GDELT}?{urllib.parse.urlencode(params)}"
    wait = MIN_INTERVAL - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", "replace")
        if not raw or not raw.strip().startswith("{"):
            return []
        arts = json.loads(raw).get("articles", []) or []
    except Exception as e:  # noqa: BLE001
        print(f"[news] {sec.symbol}: gdelt fallback failed ({e})")
        return []
    seen, items = set(), []
    for a in arts:
        title = (a.get("title") or "").strip()
        dom = a.get("domain") or ""
        key = (dom, title[:60].lower())
        if not title or key in seen:
            continue
        item = {"title": title, "url": a.get("url"), "domain": dom,
                "published_at": _parse_seendate(a.get("seendate", "")),
                "lang": a.get("language"), "source_type": "media"}
        if not _relevant(item, sec):
            continue
        seen.add(key)
        items.append(item)
        if len(items) >= limit:
            break
    return items


def fetch(symbol: str, limit: int = 8, timespan: str = "30d") -> dict | None:
    """Fetch live media for one symbol: Google News RSS first, GDELT as fallback. Honest-
    degraded: on any failure / empty result, keeps the prior cache (returns None)."""
    sec = by_symbol(symbol)
    if not sec:
        return None
    source, items = "Google News (live media)", []
    try:
        items = _fetch_google(sec, limit)
    except Exception as e:  # noqa: BLE001
        print(f"[news] {symbol}: google news failed ({e})")
    if not items:
        items = _fetch_gdelt(sec, limit, timespan)
        if items:
            source = "GDELT (live media)"
    if not items:
        print(f"[news] {symbol}: 0 articles — kept prior")
        return None
    rec = {"symbol": symbol, "retrieved_at": _iso(), "query": _query(sec),
           "source": source, "items": items}
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"{symbol}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    print(f"[news] {symbol}: {len(items)} live articles ({source.split()[0]})")
    return rec


def run_symbols(symbols: list[str]) -> int:
    n = 0
    for i, s in enumerate(symbols):
        if fetch(s.strip().upper()):
            n += 1
        if i < len(symbols) - 1:
            time.sleep(1.2)   # be polite to Google News RSS across a sweep
    print(f"[news] done: {n}/{len(symbols)} updated -> {DATA}")
    return n


def run_stale(n: int) -> int:
    min_age = float(__import__("os").environ.get("NEWS_MIN_AGE_HOURS", "6"))
    cutoff = datetime.now(UTC) - timedelta(hours=min_age)
    cands = []
    for s in load_universe():
        f = DATA / f"{s.symbol}.json"
        t = None
        if f.exists():
            try:
                t = json.loads(f.read_text()).get("retrieved_at")
            except Exception:
                t = None
        if t is None:
            cands.append(("", s.symbol))
        else:
            try:
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            except Exception:
                dt = cutoff - timedelta(days=1)
            if dt < cutoff:
                cands.append((t, s.symbol))
    cands.sort(key=lambda x: x[0])
    batch = [sym for _, sym in cands[:max(1, n)]]
    if not batch:
        print(f"[news] nothing stale (all within {min_age:.0f}h) — skip")
        return 0
    print(f"[news] stale batch ({len(batch)} of {len(cands)}): {', '.join(batch)}")
    return run_symbols(batch)


def main() -> None:
    ap = argparse.ArgumentParser(description="Live news fetcher (GDELT) for UAE stocks")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--stale", type=int, metavar="N")
    ap.add_argument("--symbols", type=str)
    args = ap.parse_args()
    if args.stale is not None:
        run_stale(args.stale)
    elif args.all:
        run_symbols([s.symbol for s in load_universe()])
    elif args.symbols:
        run_symbols(args.symbols.split(","))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
