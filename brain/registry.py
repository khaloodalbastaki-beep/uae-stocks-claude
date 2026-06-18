"""
Canonical securities registry for UAE Stocks Intelligence.

The blueprint's first rule: "store every stock as a canonical symbol record with
aliases, ISIN, exchange, sector, and document relationships first." This module is
that source of truth. Everything downstream (quotes, disclosures, scoring, AI) keys
off `Security.symbol`.

The seed list below is REAL — actual ADX / DFM ordinary-equity tickers and sectors,
plus the global-driver exposure map per name (the "global factor box"). Prices and
fundamentals are NOT here; those come from adapters and are tagged with their source
and data-quality so the UI never presents a demo number as if it were a real quote.

`research/enriched_universe.json` (produced by the grounding research run) is merged
on top of this base when present, so the universe widens without code edits.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

ADX = "ADX"
DFM = "DFM"
NASDAQ_DUBAI = "NASDAQ_DUBAI"


@dataclass
class Security:
    symbol: str
    name_en: str
    name_ar: str
    exchange: str            # ADX | DFM | NASDAQ_DUBAI
    sector: str              # canonical sector label (see SECTORS)
    archetype: str           # scoring/exposure archetype (see brain.scoring)
    exposure_factors: list[str] = field(default_factory=list)  # global drivers
    isin: str | None = None
    aliases: list[str] = field(default_factory=list)
    currency: str = "AED"

    def to_dict(self) -> dict:
        return asdict(self)


# Canonical sector labels (kept small + stable, per Khalid's "small, stable" rule).
SECTORS = [
    "Banks", "Real Estate", "Utilities", "Energy", "Petrochemicals",
    "Telecom", "Logistics & Transport", "Food & Agri", "Healthcare",
    "Holding / Diversified", "Toll Roads & Parking", "Insurance",
    "Industrials", "Consumer", "Investment & Finance",
]

# ---------------------------------------------------------------------------
# Seed universe — real UAE-listed ordinary equities.
# exposure_factors use canonical driver keys (see brain/factors.py FACTORS).
# ---------------------------------------------------------------------------
_SEED: list[Security] = [
    # ---- ADX: banks ----
    Security("FAB", "First Abu Dhabi Bank", "بنك أبوظبي الأول", ADX, "Banks", "bank",
             ["rates", "usd", "uae_credit", "oil"]),
    Security("ADCB", "Abu Dhabi Commercial Bank", "بنك أبوظبي التجاري", ADX, "Banks", "bank",
             ["rates", "usd", "uae_credit"]),
    Security("ADIB", "Abu Dhabi Islamic Bank", "مصرف أبوظبي الإسلامي", ADX, "Banks", "bank",
             ["rates", "uae_credit"]),
    # ---- ADX: energy / petrochem (ADNOC complex) ----
    Security("ADNOCGAS", "ADNOC Gas", "أدنوك للغاز", ADX, "Energy", "energy",
             ["natural_gas", "oil", "lng"]),
    Security("ADNOCDIST", "ADNOC Distribution", "أدنوك للتوزيع", ADX, "Energy", "fuel_retail",
             ["oil", "fuel_demand", "tourism"]),
    Security("ADNOCDRILL", "ADNOC Drilling", "أدنوك للحفر", ADX, "Energy", "oil_services",
             ["oil", "rig_demand"]),
    Security("ADNOCLS", "ADNOC Logistics & Services", "أدنوك للخدمات اللوجستية", ADX, "Logistics & Transport", "shipping",
             ["freight", "oil", "trade"]),
    Security("BOROUGE", "Borouge", "بروج", ADX, "Petrochemicals", "petrochem",
             ["natural_gas", "polyethylene", "oil"]),
    Security("FERTIGLB", "Fertiglobe", "فيرتيجلوب", ADX, "Petrochemicals", "fertilizer",
             ["urea", "ammonia", "natural_gas", "wheat"]),
    Security("TAQA", "Abu Dhabi National Energy (TAQA)", "طاقة", ADX, "Utilities", "utility",
             ["rates", "natural_gas", "power_demand"]),
    # ---- ADX: holdings / diversified ----
    Security("IHC", "International Holding Company", "القابضة (آي إتش سي)", ADX, "Holding / Diversified", "holding",
             ["uae_equity", "rates", "oil"]),
    Security("ALPHADHABI", "Alpha Dhabi Holding", "ألفا ظبي القابضة", ADX, "Holding / Diversified", "holding",
             ["uae_equity", "construction", "rates"]),
    Security("2POINTZERO", "Two Point Zero Group", "مجموعة تو بوينت زيرو", ADX, "Holding / Diversified", "holding",
             ["uae_equity", "consumer"], aliases=["MULTIPLY"]),  # ex-Multiply (verified rename, grounding §2.3)
    # NOTE: "Q" (Q Holding) was rebranded to Modon Holding after the Feb-2024 merger and now
    # trades as MODON (below) — removed to avoid a defunct duplicate ticker. (verified 2026-06-19)
    # ---- ADX: real estate ----
    Security("ALDAR", "Aldar Properties", "الدار العقارية", ADX, "Real Estate", "developer",
             ["rates", "construction_metals", "tourism", "population"]),
    # ---- ADX: healthcare / tech / space ----
    Security("PUREHEALTH", "Pure Health Holding", "بيور هيلث", ADX, "Healthcare", "healthcare",
             ["population", "health_spend", "tourism"]),
    Security("PRESIGHT", "Presight AI Holding", "بريسايت", ADX, "Holding / Diversified", "tech",
             ["ai_capex", "uae_gov_spend"]),
    Security("SPACE42", "Space42", "سبيس 42", ADX, "Telecom", "tech",
             ["satellite_capex", "uae_gov_spend"]),
    Security("AMERICANA", "Americana Restaurants", "أمريكانا", ADX, "Consumer", "consumer",
             ["wheat", "chicken", "consumer_demand", "tourism"], aliases=["AMR"]),
    Security("ADPORTS", "AD Ports Group", "موانئ أبوظبي", ADX, "Logistics & Transport", "ports",
             ["freight", "trade", "oil"]),
    Security("EAND", "e& (Emirates Telecom Group)", "اتصالات من إي آند", ADX, "Telecom", "telecom",
             ["usd", "em_fx", "data_demand"], aliases=["ETISALAT"]),
    # --- ADX: additional verified real names (grounding research, 2026-06-18) ---
    Security("RAKBANK", "National Bank of Ras Al Khaimah", "بنك رأس الخيمة الوطني", ADX, "Banks", "bank",
             ["rates", "uae_credit", "oil"]),
    Security("SIB", "Sharjah Islamic Bank", "مصرف الشارقة الإسلامي", ADX, "Banks", "bank",
             ["rates", "uae_credit"]),
    Security("MODON", "Modon Holding", "مدن القابضة", ADX, "Real Estate", "developer",
             ["rates", "construction_metals", "tourism", "population"]),
    Security("RAKPROP", "RAK Properties", "عقارات رأس الخيمة", ADX, "Real Estate", "developer",
             ["rates", "construction_metals", "population"]),
    Security("EMSTEEL", "Emirates Steel Arkan", "الإمارات للحديد والصلب أركان", ADX, "Industrials", "industrials",
             ["construction_metals", "construction", "natural_gas"]),
    Security("NMDC", "NMDC Group", "مجموعة إن إم دي سي", ADX, "Industrials", "industrials",
             ["construction", "oil", "trade"]),
    Security("NMDCENR", "NMDC Energy", "إن إم دي سي للطاقة", ADX, "Energy", "oil_services",
             ["oil", "oil_services", "rig_demand"]),
    Security("DANA", "Dana Gas", "دانة غاز", ADX, "Energy", "energy",
             ["oil", "natural_gas"]),
    Security("AGTHIA", "Agthia Group", "مجموعة أغذية", ADX, "Food & Agri", "consumer",
             ["wheat", "consumer_demand", "population"]),
    Security("GHITHA", "Ghitha Holding", "غذاء القابضة", ADX, "Food & Agri", "consumer",
             ["wheat", "population", "freight"]),
    Security("BURJEEL", "Burjeel Holdings", "برجيل القابضة", ADX, "Healthcare", "healthcare",
             ["population", "health_spend", "tourism"]),
    Security("JULPHAR", "Gulf Pharmaceutical Industries (Julphar)", "الخليج للصناعات الدوائية (جلفار)", ADX, "Healthcare", "healthcare",
             ["health_spend", "population"]),
    Security("ADNH", "Abu Dhabi National Hotels", "الوطنية للفنادق", ADX, "Consumer", "consumer",
             ["tourism", "consumer_demand"]),

    # ---- DFM: banks ----
    Security("EMIRATESNBD", "Emirates NBD", "بنك الإمارات دبي الوطني", DFM, "Banks", "bank",
             ["rates", "usd", "uae_credit", "tourism"]),
    Security("DIB", "Dubai Islamic Bank", "بنك دبي الإسلامي", DFM, "Banks", "bank",
             ["rates", "uae_credit"]),
    Security("CBD", "Commercial Bank of Dubai", "بنك دبي التجاري", DFM, "Banks", "bank",
             ["rates", "uae_credit"]),
    Security("MASHREQ", "Mashreqbank", "بنك المشرق", DFM, "Banks", "bank",
             ["rates", "uae_credit", "trade"], aliases=["MASQ"]),
    # ---- DFM: real estate ----
    Security("EMAAR", "Emaar Properties", "إعمار العقارية", DFM, "Real Estate", "developer",
             ["rates", "construction_metals", "tourism", "population"]),
    Security("EMAARDEV", "Emaar Development", "إعمار للتطوير", DFM, "Real Estate", "developer",
             ["rates", "construction_metals", "population"]),
    Security("DEYAAR", "Deyaar Development", "ديار للتطوير", DFM, "Real Estate", "developer",
             ["rates", "construction_metals", "population"]),
    # ---- DFM: utilities / infrastructure ----
    Security("DEWA", "Dubai Electricity & Water Authority", "ديوا", DFM, "Utilities", "utility",
             ["rates", "natural_gas", "population", "power_demand"]),
    Security("EMPOWER", "Emirates Central Cooling Systems (Empower)", "إمباور", DFM, "Utilities", "utility",
             ["rates", "power_demand", "construction_metals"]),
    Security("SALIK", "Salik Company", "سالك", DFM, "Toll Roads & Parking", "toll",
             ["traffic", "tourism", "population"]),
    Security("PARKIN", "Parkin Company", "باركن", DFM, "Toll Roads & Parking", "toll",
             ["traffic", "tourism", "population"]),
    Security("DTC", "Dubai Taxi Company", "تاكسي دبي", DFM, "Logistics & Transport", "mobility",
             ["fuel_demand", "tourism", "population"]),
    Security("TECOM", "TECOM Group", "تيكوم", DFM, "Real Estate", "developer",
             ["rates", "occupancy", "tourism"]),
    # ---- DFM: consumer / food / other ----
    Security("TALABAT", "Talabat Holding", "طلبات", DFM, "Consumer", "consumer",
             ["consumer_demand", "tourism", "fuel_demand"]),
    Security("ARMX", "Aramex", "أرامكس", DFM, "Logistics & Transport", "logistics",
             ["freight", "trade", "fuel_demand", "ecommerce"], aliases=["ARAMEX"]),
    Security("DU", "Emirates Integrated Telecommunications (du)", "دو", DFM, "Telecom", "telecom",
             ["usd", "data_demand", "population"]),
    Security("AIRARABIA", "Air Arabia", "العربية للطيران", DFM, "Logistics & Transport", "aviation",
             ["jet_fuel", "tourism", "usd"]),
    Security("GFH", "GFH Financial Group", "جي إف إتش", DFM, "Investment & Finance", "investment",
             ["uae_equity", "rates"]),
    Security("SHUAA", "SHUAA Capital", "شعاع كابيتال", DFM, "Investment & Finance", "investment",
             ["uae_equity", "rates"]),
    Security("DIN", "Dubai Insurance", "دبي للتأمين", DFM, "Insurance", "insurance",
             ["rates", "uae_credit"]),
]


def _enriched_path() -> Path:
    return Path(__file__).resolve().parent.parent / "research" / "enriched_universe.json"


def load_universe() -> list[Security]:
    """Base seed, optionally widened/overridden by the research run output."""
    by_symbol: dict[str, Security] = {s.symbol: s for s in _SEED}
    ep = _enriched_path()
    if ep.exists():
        try:
            extra = json.loads(ep.read_text())
            for row in extra:
                sym = (row.get("symbol") or "").strip().upper()
                if not sym:
                    continue
                if sym in by_symbol:
                    # only fill gaps; never clobber a curated record blindly
                    s = by_symbol[sym]
                    if not s.exposure_factors and row.get("exposure_factors"):
                        s.exposure_factors = row["exposure_factors"]
                    if not s.name_ar and row.get("name_ar"):
                        s.name_ar = row["name_ar"]
                else:
                    by_symbol[sym] = Security(
                        symbol=sym,
                        name_en=row.get("name_en", sym),
                        name_ar=row.get("name_ar", ""),
                        exchange=row.get("exchange", ADX),
                        sector=row.get("sector", "Holding / Diversified"),
                        archetype=row.get("archetype", "holding"),
                        exposure_factors=row.get("exposure_factors", []),
                        isin=row.get("isin"),
                    )
        except Exception as e:  # noqa: BLE001 — never let enrichment break the base
            print(f"[registry] enrichment skipped: {e}")
    return sorted(by_symbol.values(), key=lambda s: (s.exchange, s.symbol))


def by_symbol(symbol: str) -> Security | None:
    symbol = symbol.strip().upper()
    for s in load_universe():
        if s.symbol == symbol or symbol in (a.upper() for a in s.aliases):
            return s
    return None


if __name__ == "__main__":
    u = load_universe()
    print(f"{len(u)} securities")
    for s in u:
        print(f"  {s.exchange:14} {s.symbol:12} {s.sector:22} {s.name_en}")
