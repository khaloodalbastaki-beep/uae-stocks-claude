"""
Mock provider — realistic, DETERMINISTIC demo data so the whole app runs offline for
AED 0 with no API key. The blueprint asks for "Mock adapters for data providers so real
providers can be swapped later" and "Seed scripts for demo data."

Honesty rule (Khalid: "real data is sacred; keep test/synthetic strictly out of it"):
every object this module emits is tagged source_type=mock, data_quality=demo. The UI
renders a loud DEMO badge for these, and the ingest pipeline never writes them into a
"real" channel. Prices/fundamentals are plausible but explicitly NOT real quotes.

Determinism: each symbol seeds its own PRNG from a stable hash, so re-running the brain
produces the same demo dataset (idempotent — matches Khalid's net-new-only curation).
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone

from .base import (
    Quote, Disclosure, Meeting, DividendEvent, OwnershipSnapshot,
    CommodityPoint, GlobalEvent, Provenance,
    SOURCE_MOCK, DQ_DEMO,
    QuoteAdapter, DisclosureAdapter, CorporateActionsAdapter,
    FundamentalsAdapter, OwnershipAdapter, CommodityAdapter, EventsAdapter,
)
from ..scoring import Fundamentals
from ..registry import by_symbol
from ..factors import factor_meta

UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


def _rng(symbol: str, salt: str = "") -> random.Random:
    h = hashlib.sha256(f"{symbol}|{salt}".encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def _prov() -> Provenance:
    return Provenance(SOURCE_MOCK, "Demo seed", DQ_DEMO, _iso(_now()))


# Plausible anchor prices (AED) for well-known names; others derived from the symbol.
_ANCHOR = {
    "FAB": 14.2, "ADCB": 11.5, "ADIB": 18.6, "EMIRATESNBD": 23.0, "DIB": 7.4,
    "CBD": 8.9, "MASHREQ": 210.0, "EMAAR": 14.8, "EMAARDEV": 12.6, "DEYAAR": 0.86,
    "ALDAR": 9.4, "DEWA": 2.62, "EMPOWER": 1.78, "SALIK": 5.40, "PARKIN": 6.10,
    "DTC": 3.05, "TECOM": 4.10, "TALABAT": 1.55, "ARAMEX": 2.95, "AIRARABIA": 3.42,
    "ADNOCGAS": 3.55, "ADNOCDIST": 4.18, "ADNOCDRILL": 6.05, "ADNOCLS": 5.30,
    "BOROUGE": 2.55, "FERTIGLB": 3.10, "TAQA": 3.30, "IHC": 400.0, "ALPHADHABI": 12.5,
    "MULTIPLY": 2.40, "Q": 3.20, "PUREHEALTH": 4.05, "PRESIGHT": 2.85, "SPACE42": 2.60,
    "AMERICANA": 2.95, "ADPORTS": 5.40, "ETISALAT": 18.4, "GFH": 3.05, "SHUAA": 0.36,
    "DIN": 6.50,
}

_DISCLOSURE_TEMPLATES = [
    ("results", "Financial results for the period", "نتائج مالية للفترة", "ar",
     "Board approved the interim financial statements; revenue and net profit disclosed."),
    ("board_meeting", "Board of Directors meeting invitation", "دعوة لاجتماع مجلس الإدارة", "ar",
     "Board to convene to discuss results and a proposed cash dividend."),
    ("agm_invitation", "Invitation to the General Assembly Meeting", "دعوة للجمعية العمومية", "ar",
     "AGM agenda includes dividend approval, board election and auditor appointment."),
    ("dividend", "Cash dividend distribution announcement", "الإعلان عن توزيع أرباح نقدية", "ar",
     "Company announces a cash dividend per share with entitlement and payment dates."),
    ("acquisition", "Acquisition / strategic transaction", "استحواذ / صفقة استراتيجية", "en",
     "Company entered an agreement to acquire a strategic asset, subject to approvals."),
    ("capital_raise", "Capital increase / sukuk issuance", "زيادة رأس المال / إصدار صكوك", "en",
     "Board approved a capital markets transaction to fund expansion."),
    ("governance", "Governance / board change", "تغيير في الحوكمة / المجلس", "en",
     "Change in senior leadership / board composition disclosed."),
    ("subsidiary", "Subsidiary event", "حدث متعلق بشركة تابعة", "en",
     "Material development at a subsidiary disclosed to the market."),
]

_SENTI = ["positive", "neutral", "cautious", "negative"]


class MockProvider(QuoteAdapter, DisclosureAdapter, CorporateActionsAdapter,
                   FundamentalsAdapter, OwnershipAdapter, CommodityAdapter, EventsAdapter):
    name = "mock"

    # ---- quotes ----
    def get_quote(self, symbol: str) -> Quote | None:
        sec = by_symbol(symbol)
        if not sec:
            return None
        r = _rng(symbol, "quote")
        base = _ANCHOR.get(symbol, round(0.5 + r.random() * 12, 2))
        chg_pct = round(r.uniform(-0.035, 0.035), 4)
        price = round(base * (1 + chg_pct), 2 if base < 100 else 1)
        change = round(price - base, 3)
        # 30-day sparkline as a gentle random walk around base
        spark, p = [], base * (1 - r.uniform(0, 0.06))
        for _ in range(30):
            p = max(0.05, p * (1 + r.uniform(-0.02, 0.022)))
            spark.append(round(p, 3))
        spark[-1] = price
        shares = r.uniform(2e9, 9e9) if base < 50 else r.uniform(1e8, 2e9)
        mcap = round(price * shares, -6)
        return Quote(
            symbol=symbol, price=price, change=change, change_pct=chg_pct,
            volume=int(r.uniform(1e5, 4e7)), market_cap=mcap,
            high_52w=round(max(spark) * 1.08, 2), low_52w=round(min(spark) * 0.9, 2),
            spark=spark, prov=_prov(),
        )

    # ---- fundamentals (archetype-shaped, varied) ----
    def get_fundamentals(self, symbol: str) -> Fundamentals:
        sec = by_symbol(symbol)
        arc = sec.archetype if sec else "holding"
        r = _rng(symbol, "fund")
        f = Fundamentals()
        # base ranges
        f.revenue_growth = round(r.uniform(-0.04, 0.22), 4)
        f.profit_growth = round(f.revenue_growth + r.uniform(-0.06, 0.12), 4)
        f.revenue_cagr_3y = round(max(0.0, f.revenue_growth * r.uniform(0.5, 1.2)), 4)
        f.margin_trend = round(r.uniform(-0.02, 0.03), 4)
        f.reinvestment = round(r.uniform(0.3, 0.85), 2)
        f.catalysts = r.randint(0, 4)
        f.net_debt_to_ebitda = round(r.uniform(0.4, 4.5), 2)
        f.current_ratio = round(r.uniform(0.9, 2.0), 2)
        f.ocf_consistency = round(r.uniform(0.45, 0.95), 2)
        f.price_volatility = round(r.uniform(0.15, 0.5), 3)
        f.governance_cadence = round(r.uniform(0.5, 0.95), 2)
        f.disclosure_quality = round(r.uniform(0.5, 0.95), 2)
        f.macro_sensitivity = round(r.uniform(0.2, 0.85), 2)
        f.dividend_yield = round(max(0.0, r.uniform(-0.01, 0.085)), 4)
        f.payout_ratio = round(r.uniform(0.2, 0.85), 2)
        f.fcf_coverage = round(r.uniform(0.6, 2.2), 2)
        f.net_debt_pressure = round(r.uniform(0.1, 0.8), 2)
        f.cut_history = r.choices([0, 0, 0, 1, 2], k=1)[0]
        f.frequency = r.choices(["annual", "annual", "semi", "quarterly", "none"], k=1)[0]
        f.years_paid = r.randint(0, 8)

        # archetype shaping for realism
        if arc == "bank":
            f.net_debt_to_ebitda = round(r.uniform(0.5, 1.5), 2)   # not meaningful for banks; keep low
            f.dividend_yield = round(r.uniform(0.04, 0.075), 4)
            f.ocf_consistency = round(r.uniform(0.7, 0.95), 2)
            f.macro_sensitivity = round(r.uniform(0.4, 0.7), 2)
            f.frequency = r.choice(["annual", "semi"])
        elif arc in ("utility", "toll"):
            f.dividend_yield = round(r.uniform(0.045, 0.08), 4)
            f.ocf_consistency = round(r.uniform(0.75, 0.97), 2)
            f.price_volatility = round(r.uniform(0.12, 0.28), 3)
            f.fcf_coverage = round(r.uniform(1.0, 1.8), 2)
            f.frequency = r.choice(["semi", "quarterly"])
        elif arc == "developer":
            f.macro_sensitivity = round(r.uniform(0.55, 0.9), 2)
            f.price_volatility = round(r.uniform(0.3, 0.55), 3)
            f.revenue_growth = round(r.uniform(0.0, 0.3), 4)
        elif arc in ("holding", "tech", "investment"):
            f.dividend_yield = round(max(0.0, r.uniform(-0.02, 0.03)), 4)
            f.price_volatility = round(r.uniform(0.3, 0.6), 3)
        return f

    # ---- disclosures ----
    def list_disclosures(self, symbol: str, limit: int = 20) -> list[Disclosure]:
        sec = by_symbol(symbol)
        if not sec:
            return []
        r = _rng(symbol, "disc")
        n = r.randint(4, 9)
        out: list[Disclosure] = []
        for i in range(n):
            ev, ten, tar, lang, body = r.choice(_DISCLOSURE_TEMPLATES)
            days_ago = int(r.uniform(0, 90))
            pub = _now() - timedelta(days=days_ago, hours=int(r.uniform(0, 12)))
            mat = r.randint(25, 95) if ev in ("results", "dividend", "acquisition", "capital_raise") else r.randint(15, 70)
            out.append(Disclosure(
                id=f"{symbol}-{i}-{int(pub.timestamp())}",
                symbol=symbol,
                event_type=ev,
                title_src=(tar if lang == "ar" else ten),
                title_en=ten,
                title_lang=lang,
                published_at=_iso(pub),
                body_excerpt=body,
                url=None,
                materiality=mat,
                sentiment=r.choices(_SENTI, weights=[3, 4, 2, 1])[0],
                linked_entities=[],
                prov=_prov(),
                translation_app_generated=(lang == "ar"),
            ))
        out.sort(key=lambda d: d.published_at, reverse=True)
        return out[:limit]

    # ---- meetings ----
    def meetings(self, symbol: str) -> list[Meeting]:
        sec = by_symbol(symbol)
        if not sec:
            return []
        r = _rng(symbol, "mtg")
        out: list[Meeting] = []
        # one upcoming board meeting + one upcoming/just-held AGM + a past board
        up_board = _now() + timedelta(days=int(r.uniform(3, 35)))
        out.append(Meeting(symbol, "board", up_board.date().isoformat(), "upcoming",
                           agenda=["Review interim results", "Consider cash dividend"],
                           topics=["dividend"], prov=_prov()))
        agm = _now() + timedelta(days=int(r.uniform(20, 80)))
        out.append(Meeting(symbol, "agm", agm.date().isoformat(), "upcoming",
                           agenda=["Approve dividend", "Elect board", "Appoint auditor"],
                           topics=["dividend", "board_election"], prov=_prov()))
        past = _now() - timedelta(days=int(r.uniform(40, 200)))
        out.append(Meeting(symbol, "board", past.date().isoformat(), "held",
                           agenda=["Approve annual results"], topics=["dividend", "buyback"],
                           resolutions=["Approved annual results", "Recommended cash dividend"],
                           outcome_summary="Annual results approved; dividend recommended to AGM.",
                           prov=_prov()))
        return out

    # ---- dividends ----
    def dividends(self, symbol: str) -> list[DividendEvent]:
        sec = by_symbol(symbol)
        if not sec:
            return []
        f = self.get_fundamentals(symbol)
        if f.frequency == "none" or f.dividend_yield <= 0:
            return []
        r = _rng(symbol, "div")
        q = self.get_quote(symbol)
        price = q.price if q else 5.0
        per_year = {"annual": 1, "semi": 2, "quarterly": 4}.get(f.frequency, 1)
        total = price * f.dividend_yield
        per_event = round(total / per_year, 4)
        out: list[DividendEvent] = []
        # last 2 years of events
        for k in range(per_year * 2):
            ref = _now() - timedelta(days=int(365 / per_year) * k + int(r.uniform(0, 20)))
            out.append(DividendEvent(
                symbol=symbol, amount=per_event, agm_date=(ref - timedelta(days=20)).date().isoformat(),
                entitlement_date=(ref - timedelta(days=2)).date().isoformat(),
                ex_date=(ref - timedelta(days=3)).date().isoformat(),
                payment_date=(ref + timedelta(days=14)).date().isoformat(),
                frequency=f.frequency, fiscal_year=str(ref.year), prov=_prov(),
            ))
        # one upcoming
        up = _now() + timedelta(days=int(r.uniform(10, 50)))
        out.insert(0, DividendEvent(
            symbol=symbol, amount=per_event, agm_date=(up - timedelta(days=15)).date().isoformat(),
            entitlement_date=(up + timedelta(days=5)).date().isoformat(),
            ex_date=(up + timedelta(days=4)).date().isoformat(),
            payment_date=(up + timedelta(days=25)).date().isoformat(),
            frequency=f.frequency, fiscal_year=str(up.year), prov=_prov(),
        ))
        return out

    # ---- ownership ----
    def get_ownership(self, symbol: str) -> OwnershipSnapshot | None:
        sec = by_symbol(symbol)
        if not sec:
            return None
        r = _rng(symbol, "own")
        gov = round(r.uniform(20, 65), 1)
        strategic = round(r.uniform(5, 20), 1)
        free = round(100 - gov - strategic, 1)
        fperm = round(r.choice([40, 49, 100]), 1)
        factual = round(min(fperm, r.uniform(5, fperm)), 1)
        return OwnershipSnapshot(
            symbol=symbol,
            top_holders=[
                {"name": "Government / sovereign entity", "pct": gov},
                {"name": "Strategic shareholder", "pct": strategic},
                {"name": "Free float", "pct": free},
            ],
            foreign_permitted=fperm, foreign_actual=factual,
            foreign_available=round(max(0, fperm - factual), 1),
            free_float=free, prov=_prov(),
        )

    # ---- commodities ----
    def snapshot(self) -> list[CommodityPoint]:
        r = _rng("GLOBAL", "cmo")
        series = [
            ("CRUDE_BRENT", "Brent crude", 78.0, "USD/bbl"),
            ("NGAS_EUR", "Natural gas (EU)", 11.5, "USD/mmbtu"),
            ("ALUMINUM", "Aluminium", 2450.0, "USD/mt"),
            ("UREA_EE_BULK", "Urea", 360.0, "USD/mt"),
            ("WHEAT_US_HRW", "Wheat", 245.0, "USD/mt"),
            ("GOLD", "Gold", 2380.0, "USD/oz"),
        ]
        out = []
        for s, label, base, unit in series:
            chg = round(r.uniform(-0.04, 0.04), 4)
            out.append(CommodityPoint(s, label, round(base * (1 + chg), 2), chg, unit,
                                      _iso(_now()), _prov()))
        return out

    # ---- global events (GDELT-shaped) ----
    def global_events(self, query: str, limit: int = 8) -> list[GlobalEvent]:
        r = _rng(query, "evt")
        themes = ["ENERGY", "ECON_INTEREST_RATE", "TRADE", "MARITIME", "AGRICULTURE", "TOURISM"]
        domains = ["reuters.com", "bloomberg.com", "wam.ae", "thenationalnews.com", "gulfnews.com"]
        out = []
        for i in range(min(limit, r.randint(3, 6))):
            t = r.choice(themes)
            out.append(GlobalEvent(
                title=f"{query.split()[0].title()} headline — global macro update {i+1}",
                theme=t,
                published_at=_iso(_now() - timedelta(hours=int(r.uniform(1, 72)))),
                domain=r.choice(domains),
                url=None,
                tone=round(r.uniform(-6, 6), 2),
                prov=Provenance(SOURCE_MOCK, "GDELT (demo)", DQ_DEMO, _iso(_now())),
            ))
        return out
