"""
Real-fundamentals store. Reads data/fundamentals/<SYMBOL>.json (written by the Mizan
agent or seeded from verified filings) and converts the *reported* figures into the
deterministic scoring.Fundamentals.

Khalid's rule holds: the LLM (Mizan) only TRANSCRIBES reported figures from a filing — it
never computes a score. This module then derives growth/margins/leverage/coverage from
those reported numbers with plain arithmetic, and brain.scoring turns them into the house
scores. So every score is still code-computed; the only thing sourced from the model is
the transcription of what the company actually reported, carried with a source URL + date.

Record schema (one file per symbol):
{
  "symbol": "FAB", "as_of": "2025-12-31", "currency": "AED",
  "source": "FAB FY2025 results", "source_url": "https://…",
  "extractor": "mizan/groq" | "manual-verified", "confidence": "high|medium|low",
  "reported": {
     "revenue", "revenue_prior", "net_income", "net_income_prior",
     "net_margin", "net_margin_prior", "total_debt", "ebitda",
     "operating_cash_flow", "current_ratio", "dividend_per_share",
     "payout_ratio", "fcf", "cut_history_5y", "dividend_frequency", "years_paid"
  }
}
Every field in `reported` is optional; missing ones fall back to a sensible neutral.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..scoring import Fundamentals


def _fnum(d: dict, *keys, default=None):
    for k in keys:
        v = d.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return default


class FundamentalsStore:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir) / "fundamentals"
        self._cache: dict[str, dict] = {}

    def record(self, symbol: str) -> dict | None:
        if symbol in self._cache:
            return self._cache[symbol]
        f = self.dir / f"{symbol}.json"
        if not f.exists():
            self._cache[symbol] = None
            return None
        try:
            rec = json.loads(f.read_text())
            self._cache[symbol] = rec
            return rec
        except Exception as e:  # noqa: BLE001
            print(f"[fundamentals] {symbol} parse failed: {e}")
            self._cache[symbol] = None
            return None

    def has_real(self, symbol: str) -> bool:
        return self.record(symbol) is not None

    def to_fundamentals(self, symbol: str, price: float | None) -> Fundamentals | None:
        """Derive deterministic Fundamentals from the reported figures. Returns None if no
        real record (caller falls back to the modeled provider)."""
        rec = self.record(symbol)
        if not rec:
            return None
        r = rec.get("reported", {}) or {}
        f = Fundamentals()

        rev = _fnum(r, "revenue"); rev0 = _fnum(r, "revenue_prior")
        ni = _fnum(r, "net_income"); ni0 = _fnum(r, "net_income_prior")
        if rev and rev0 and rev0 != 0:
            f.revenue_growth = round((rev - rev0) / abs(rev0), 4)
            f.revenue_cagr_3y = max(0.0, f.revenue_growth)  # 1y proxy unless a 3y series given
        if ni and ni0 and ni0 != 0:
            f.profit_growth = round((ni - ni0) / abs(ni0), 4)

        nm = _fnum(r, "net_margin"); nm0 = _fnum(r, "net_margin_prior")
        if nm is None and rev and ni:
            nm = ni / rev
        if nm is not None and nm0 is not None:
            f.margin_trend = round(nm - nm0, 4)

        debt = _fnum(r, "total_debt", "net_debt"); ebitda = _fnum(r, "ebitda")
        if debt is not None and ebitda and ebitda != 0:
            f.net_debt_to_ebitda = round(max(0.0, debt / ebitda), 2)
        cr = _fnum(r, "current_ratio")
        if cr is not None:
            f.current_ratio = round(cr, 2)

        ocf = _fnum(r, "operating_cash_flow")
        if ocf is not None and ni:
            f.ocf_consistency = round(max(0.3, min(1.0, ocf / abs(ni))) if ni else 0.7, 2)

        dps = _fnum(r, "dividend_per_share")
        if dps is not None and price:
            f.dividend_yield = round(max(0.0, dps / price), 4)
        pr = _fnum(r, "payout_ratio")
        if pr is not None:
            f.payout_ratio = round(pr, 2)
        fcf = _fnum(r, "fcf", "free_cash_flow")
        div_total = _fnum(r, "dividends_total")
        if fcf is not None and div_total and div_total != 0:
            f.fcf_coverage = round(max(0.0, fcf / div_total), 2)
        elif fcf is not None and ni and ni != 0:
            f.fcf_coverage = round(max(0.4, min(2.5, fcf / abs(ni))), 2)

        ch = r.get("cut_history_5y")
        if isinstance(ch, (int, float)):
            f.cut_history = int(ch)
        freq = r.get("dividend_frequency")
        if isinstance(freq, str) and freq:
            f.frequency = freq
        yp = r.get("years_paid")
        if isinstance(yp, (int, float)):
            f.years_paid = int(yp)

        # leverage/macro defaults stay if the filing didn't give them; governance/disclosure
        # default to "good" since a real filing implies regular reporting.
        f.governance_cadence = 0.8
        f.disclosure_quality = 0.85
        return f
