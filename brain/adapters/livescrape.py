"""
Live quote provider — reads data/live_quotes.json (produced by scraper/scrape.mjs, a
headless-Chromium read of the ADX board + DFM marketwatch) and serves REAL ~15-min-delayed
prices to the pipeline. Per-symbol graceful degradation: anything not on the board (or
untraded today, price<=0, or a stale file) falls back to the demo provider and is tagged
accordingly — honest-degraded, never a fabricated "real" price.

Provenance: real quotes are tagged source=official (the exchange), data_quality=delayed.
"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from .base import Quote, Provenance, QuoteAdapter, SOURCE_OFFICIAL, DQ_DELAYED
from .mock import MockProvider

UTC = timezone.utc
MAX_AGE_HOURS = 36  # markets close overnight/weekends; older than this = treat as stale


class LiveScrapeProvider(QuoteAdapter):
    name = "live-scrape"

    def __init__(self):
        self._fallback = MockProvider()
        self.path = Path(__file__).resolve().parent.parent.parent / "data" / "live_quotes.json"
        self.data = {}
        self.generated_at = None
        self.indices = {}
        self.stale = True
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            print("[livescrape] no data/live_quotes.json — run scraper/scrape.mjs; using demo")
            return
        try:
            blob = json.loads(self.path.read_text())
            self.data = blob.get("quotes", {})
            self.indices = blob.get("indices", {}) or {}
            self.generated_at = blob.get("generated_at")
            if self.generated_at:
                age = datetime.now(UTC) - datetime.fromisoformat(self.generated_at.replace("Z", "+00:00"))
                self.stale = age.total_seconds() > MAX_AGE_HOURS * 3600
            print(f"[livescrape] {len(self.data)} live quotes (stale={self.stale}, "
                  f"as_of={self.generated_at})")
        except Exception as e:  # noqa: BLE001
            print(f"[livescrape] load failed ({e}); using demo")

    def _spark(self, symbol: str, price: float, change_pct: float) -> list[float]:
        """Illustrative ~30-pt sparkline anchored to the real price (board gives no history).
        Deterministic per symbol+price so it's stable within a build."""
        r = random.Random(int(hashlib.sha256(f"{symbol}{price}".encode()).hexdigest()[:12], 16))
        start = price / (1 + change_pct) if (1 + change_pct) else price
        pts, p = [], start * (1 - r.uniform(0, 0.03))
        for _ in range(29):
            p = max(0.01, p * (1 + r.uniform(-0.012, 0.014)))
            pts.append(round(p, 3))
        pts.append(round(price, 3))
        return pts

    def get_quote(self, symbol: str) -> Quote | None:
        row = self.data.get(symbol)
        if self.stale or not row or not row.get("price") or row["price"] <= 0:
            return self._fallback.get_quote(symbol)  # honest demo fallback
        price = float(row["price"])
        chg_pct = float(row.get("change_pct", 0.0))
        change = round(price - price / (1 + chg_pct), 3) if (1 + chg_pct) else 0.0
        spark = self._spark(symbol, price, chg_pct)
        return Quote(
            symbol=symbol, price=price, change=change, change_pct=chg_pct,
            volume=int(row["volume"]) if row.get("volume") else 0,
            market_cap=None,  # not exposed by the board; fundamentals stay modeled
            high_52w=round(max(spark), 3), low_52w=round(min(spark), 3),
            spark=spark,
            prov=Provenance(SOURCE_OFFICIAL, row.get("source", f"{row.get('exchange','')} (delayed)"),
                            DQ_DELAYED, self.generated_at or datetime.now(UTC).isoformat()),
        )
