"""
GDELT DOC 2.0 adapter — LIVE, free, no API key, stdlib-only.

The blueprint names GDELT as the multilingual global-event layer ("monitors global
broadcast, print, and web news in more than 100 languages with updates every 15
minutes"). The DOC 2.0 API is a free GET endpoint that returns JSON:

    https://api.gdeltproject.org/api/v2/doc/doc?query=<q>&mode=ArtList&format=json
        &maxrecords=<n>&timespan=<e.g. 3d>&sort=DateDesc

Graceful degradation (Khalid's quality bar: honest-degraded beats fake-good): on any
network/parse failure we fall back to the mock provider and tag the data accordingly,
rather than fabricating a "complete" feed.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .base import GlobalEvent, Provenance, EventsAdapter, SOURCE_MEDIA, DQ_DELAYED
from .mock import MockProvider

GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"
UTC = timezone.utc

# Grounding research [VERIFIED 2026-06-18]: GDELT DOC 2.0 hard-limits ~1 request / 5s
# per IP and returns HTTP 429 (plaintext) when exceeded. We space calls ≥5s within a
# build and back off on 429, so the whole-universe ingest never trips the limit.
_MIN_INTERVAL = 5.2
_last_call = [0.0]


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0, tzinfo=UTC).isoformat()


def _parse_gdelt_date(s: str) -> str:
    # GDELT seendate format: 20260615T103000Z
    try:
        dt = datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        return _iso(dt)
    except Exception:
        return s


class GdeltProvider(EventsAdapter):
    name = "gdelt-live"

    def __init__(self, timeout: float = 8.0, timespan: str = "3d"):
        self.timeout = timeout
        self.timespan = timespan
        self._fallback = MockProvider()

    def global_events(self, query: str, limit: int = 8) -> list[GlobalEvent]:
        params = {
            "query": query, "mode": "ArtList", "format": "json",
            "maxrecords": str(max(1, min(limit, 25))), "timespan": self.timespan,
            "sort": "DateDesc",
        }
        url = f"{GDELT_DOC}?{urllib.parse.urlencode(params)}"
        try:
            # respect the 5s/IP rate limit (space since the last live call)
            wait = _MIN_INTERVAL - (time.monotonic() - _last_call[0])
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(url, headers={"User-Agent": "uae-stocks-intel/1.0"})
            try:
                resp = urllib.request.urlopen(req, timeout=self.timeout)
            except urllib.error.HTTPError as he:
                if he.code == 429:  # backoff once, then fall back rather than spin
                    time.sleep(_MIN_INTERVAL)
                    resp = urllib.request.urlopen(req, timeout=self.timeout)
                else:
                    raise
            with resp as r:
                payload = json.loads(r.read().decode("utf-8", "replace"))
            _last_call[0] = time.monotonic()
            arts = payload.get("articles", []) or []
            out: list[GlobalEvent] = []
            for a in arts[:limit]:
                out.append(GlobalEvent(
                    title=a.get("title", "").strip() or "(untitled)",
                    theme=query.split()[0].upper(),
                    published_at=_parse_gdelt_date(a.get("seendate", "")),
                    domain=a.get("domain", ""),
                    url=a.get("url"),
                    tone=0.0,
                    prov=Provenance(SOURCE_MEDIA, "GDELT", DQ_DELAYED, _iso(datetime.now(UTC)),
                                    url=a.get("url"), lang=a.get("language")),
                ))
            if out:
                return out
            # empty result is legitimate; fall through to demo so the tab isn't blank
            return self._fallback.global_events(query, limit)
        except Exception as e:  # noqa: BLE001
            print(f"[gdelt] live fetch failed ({e}); using demo fallback")
            return self._fallback.global_events(query, limit)
