"""
ADX / DFM live-exchange adapters — documented, real-ready stubs.

Why stubs and not live scraping today:
  Khalid's "real data is sacred" + the blueprint's #1 risk ("Data rights ... ADX and DFM
  both restrict how site content can be reused"). ADX Terms of Use forbid copying /
  derivative works without authorisation; DFM marks English as informational-only and
  Arabic as the official text. So the responsible launch posture (blueprint's own
  recommendation) is: ship on PUBLIC DELAYED quotes + OFFICIAL DISCLOSURES via the
  documented endpoints, and only switch on redistribution once a licensed vendor
  agreement exists. We therefore wire the *interface* now and gate the live fetch behind
  an explicit UAE_PROVIDER=live + per-source enable flags, defaulting to demo.

The grounding research run (research/grounding.md) fills the exact verified endpoint
URLs/params into ENDPOINTS below; until a source is verified+enabled it cleanly falls
back to the mock provider so the app is never blank.
"""
from __future__ import annotations

import os

from .base import (
    Quote, Disclosure, QuoteAdapter, DisclosureAdapter,
)
from .mock import MockProvider

# Endpoint surface captured by the grounding research (research/grounding.md §2).
# `verified` stays False on purpose: the *endpoints* were observed live, but the
# *right to redistribute* their data in a third-party app was NOT confirmed (ADX Terms
# were Cloudflare-blocked) and the gateway needs a Bearer token the web app self-mints —
# pulling it programmatically is effectively scraping. So live stays OFF until a licensed
# vendor feed (ICE/LSEG) or an explicit terms review clears it. Honest-by-default.
ENDPOINTS: dict[str, dict] = {
    "ADX": {
        # https://apigateway.adx.ae — GET, needs Authorization: Bearer minted via
        # www.adx.ae/api/bpm/get-cookie?getAllCookie=true. Namespace 'marketwatch-delayed'
        # = 15-minute delayed (the only public tier).
        "base": "https://apigateway.adx.ae",
        "board": "/adx/marketwatch-delayed/1.1/securityBoard/marketwatch",
        "universe": "/adx/lookups/1.1/data/listed-companies",
        "symbol_sector": "/adx/lookups/1.1/data/symbol-sector",
        "index": "/adx/marketwatch/1.1/indexChartDay/FADGI",  # also FADX15
        "disclosures": "/adx/tradings/1.1/news/category",
        "disclosure_pdf": "/adx/cdn/1.0/content/download/{id}",
        "envelope": {"resultCode": "S|F", "fields": ["response", "resultMessage", "errorMessages"]},
        "delay": "15min",
        "verified": False,      # endpoints observed; redistribution rights NOT confirmed
    },
    "DFM": {
        # delayed socket.io v1 gateway dfeed.dfm.ae (real-time = rfeed.dfm.ae, paid).
        # Snapshot JSON via POST marketwatch.dfm.ae/dapi/fetch (session-cookie, unstable).
        "delayed_feed": "wss://dfeed.dfm.ae",
        "snapshot": "https://marketwatch.dfm.ae/dapi/fetch",
        "foreign_ownership": "https://www.dfm.ae/the-exchange/statistics-reports/foreign-ownership",
        "delay": "15min",
        "verified": False,
    },
}


def _live_enabled(exchange: str) -> bool:
    if os.environ.get("UAE_PROVIDER", "mock").lower() != "live":
        return False
    if not ENDPOINTS.get(exchange, {}).get("verified"):
        return False
    return os.environ.get(f"ENABLE_{exchange}_LIVE", "0") == "1"


class ExchangeProvider(QuoteAdapter, DisclosureAdapter):
    """One provider that routes to the correct exchange by the security's exchange field."""
    name = "exchange-live"

    def __init__(self):
        self._fallback = MockProvider()

    def get_quote(self, symbol: str) -> Quote | None:
        from ..registry import by_symbol
        sec = by_symbol(symbol)
        if sec and _live_enabled(sec.exchange):
            try:
                return self._fetch_quote_live(sec.exchange, symbol)
            except Exception as e:  # noqa: BLE001
                print(f"[exchange] live quote {symbol} failed ({e}); demo fallback")
        return self._fallback.get_quote(symbol)

    def list_disclosures(self, symbol: str, limit: int = 20) -> list[Disclosure]:
        from ..registry import by_symbol
        sec = by_symbol(symbol)
        if sec and _live_enabled(sec.exchange):
            try:
                return self._fetch_disclosures_live(sec.exchange, symbol, limit)
            except Exception as e:  # noqa: BLE001
                print(f"[exchange] live disclosures {symbol} failed ({e}); demo fallback")
        return self._fallback.list_disclosures(symbol, limit)

    # --- to be implemented when endpoints are verified + licensed ---
    def _fetch_quote_live(self, exchange: str, symbol: str) -> Quote | None:
        raise NotImplementedError(
            f"{exchange} live quote endpoint not yet verified/licensed — see research/grounding.md"
        )

    def _fetch_disclosures_live(self, exchange: str, symbol: str, limit: int) -> list[Disclosure]:
        raise NotImplementedError(
            f"{exchange} live disclosures endpoint not yet verified/licensed — see research/grounding.md"
        )
