"""
Deterministic fair-value (intrinsic value) engine for UAE equities.

Khalid's rule holds: numbers from CODE, never an LLM. This module computes a per-share
fair value from REPORTED figures (earnings / equity / dividends / shares + a multi-year
series) using standard, transparent valuation methods, blended by archetype. No model ever
produces a price target — it only narrates the output elsewhere.

Methods (each returns a per-share AED value, or None when its inputs are missing):
  - DDM (Gordon growth)   — dividend payers      : fair = D1 / (r - g)
  - Justified P/B (ROE)   — banks / holdings      : fair = (ROE - g)/(r - g) * book_value_per_share
  - Earnings multiple     — everyone w/ EPS       : fair = EPS * target_PE(archetype, growth)
  - FCF perpetuity        — when FCF is reported   : fair = (FCF/share)*(1+g)/r

The available methods are blended with archetype weights into one fair_value, with the
upside vs the live price, the per-method breakdown, the assumptions (r, g, ROE) and a
confidence derived from data completeness + how tightly the methods agree. Every value is
clamped to sane bounds; honest-degraded (returns None or a partial result) when inputs are
too thin. This is research support, NOT investment advice.
"""
from __future__ import annotations

from statistics import median

# Cost of equity per archetype: ~AED risk-free (≈4.25%) + equity risk premium scaled by a
# rough sector beta. Lower for regulated/utility/toll cash flows, higher for cyclical/energy.
COST_OF_EQUITY = {
    "bank": 0.105, "insurance": 0.10, "investment": 0.115, "holding": 0.11,
    "developer": 0.12, "consumer": 0.10, "tech": 0.13, "healthcare": 0.105,
    "telecom": 0.09, "utility": 0.085, "toll": 0.085, "ports": 0.10,
    "shipping": 0.11, "logistics": 0.105, "mobility": 0.10, "aviation": 0.115,
    "energy": 0.105, "oil_services": 0.115, "petrochem": 0.115, "fertilizer": 0.115,
    "industrials": 0.11, "fuel_retail": 0.095,
}
DEFAULT_R = 0.105

# Baseline "through-cycle" P/E per archetype, before a growth tilt.
BASE_PE = {
    "bank": 9, "insurance": 10, "investment": 9, "holding": 11,
    "developer": 9, "consumer": 16, "tech": 24, "healthcare": 20,
    "telecom": 13, "utility": 14, "toll": 18, "ports": 14, "shipping": 9,
    "logistics": 16, "mobility": 15, "aviation": 9, "energy": 11,
    "oil_services": 12, "petrochem": 11, "fertilizer": 10, "industrials": 11,
    "fuel_retail": 16,
}
DEFAULT_PE = 12

# Method weights by archetype family (re-normalised over whichever methods are available).
#   keys: pb (justified P/B), ddm (dividend discount), pe (earnings multiple), fcf
_FAMILY_WEIGHTS = {
    "financial": {"pb": 0.50, "pe": 0.30, "ddm": 0.20, "fcf": 0.0},   # banks/holdings/insurers/investment
    "yield":     {"ddm": 0.45, "pe": 0.35, "pb": 0.20, "fcf": 0.0},   # utility/toll/telecom
    "growth":    {"pe": 0.55, "ddm": 0.20, "pb": 0.25, "fcf": 0.0},   # everything else
}
_FINANCIAL = {"bank", "insurance", "investment", "holding"}
_YIELD = {"utility", "toll", "telecom"}


def _family(archetype: str) -> str:
    if archetype in _FINANCIAL:
        return "financial"
    if archetype in _YIELD:
        return "yield"
    return "growth"


def _num(v):
    return float(v) if isinstance(v, (int, float)) and v == v else None


def _series_cagr(series: dict, key: str) -> float | None:
    """Annualised growth of the first→last non-null point of a reported series."""
    if not isinstance(series, dict):
        return None
    vals = [(_num(x)) for x in (series.get(key) or [])]
    pts = [v for v in vals if v is not None]
    if len(pts) < 2:
        return None
    first, last = pts[0], pts[-1]
    n = len(pts) - 1
    if first is None or first <= 0 or last <= 0:
        return None
    try:
        return (last / first) ** (1.0 / n) - 1.0
    except Exception:
        return None


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def fair_value(record: dict, price: float | None, archetype: str = "holding") -> dict | None:
    """Compute a blended per-share fair value. Returns None if there's nothing to value
    (no EPS/earnings, no equity, no dividend) or no usable price."""
    if not record or not price or price <= 0:
        return None
    r = record.get("reported", {}) or {}
    series = record.get("series", {}) or {}

    shares = _num(r.get("shares_outstanding"))
    equity = _num(r.get("total_equity"))
    # Latest net income comes from the absolute-AED SERIES (the seed `reported.net_income` is
    # mixed-unit across names — millions for some, absolute for others — so it's unsafe for
    # level math like ROE/EPS). Fall back to reported only if there's no series.
    def _latest(key):
        for v in reversed(series.get(key) or []):
            if isinstance(v, (int, float)) and v == v:
                return float(v)
        return None
    ni = _latest("net_income")
    if ni is None:
        ni = _num(r.get("net_income"))
    eps = _num(r.get("eps"))
    if eps is None and ni is not None and shares:
        eps = ni / shares
    dps = _num(r.get("dividend_per_share"))
    payout = _num(r.get("payout_ratio"))
    if payout is not None and payout > 1.5:
        payout /= 100.0   # seed stores payout as a percent for some names
    fcf = _num(r.get("fcf")) or _num(r.get("free_cash_flow"))
    bvps = (equity / shares) if (equity is not None and shares) else _num(r.get("book_value_per_share"))

    roe = None
    if ni is not None and equity and equity > 0:
        roe = _clamp(ni / equity, -0.5, 0.6)

    disc = COST_OF_EQUITY.get(archetype, DEFAULT_R)

    # ---- growth estimate g: blend reported series growth + sustainable growth, conservative
    proxies = []
    for k in ("net_income", "revenue"):
        c = _series_cagr(series, k)
        if c is not None:
            proxies.append(_clamp(c, -0.10, 0.30))
    if roe is not None and payout is not None:
        proxies.append(_clamp(roe * (1.0 - _clamp(payout, 0.0, 1.0)), 0.0, 0.20))
    elif roe is not None:
        proxies.append(_clamp(roe * 0.4, 0.0, 0.20))
    # near-term growth (drives the P/E tilt) vs PERPETUAL growth (terminal models). A terminal
    # growth near the discount rate makes Gordon/RI explode, so cap it low and keep a >=3.5pt
    # spread below r — the standard guardrail for perpetuity valuation.
    g_near = _clamp(median(proxies), 0.0, 0.10) if proxies else 0.03

    w = _FAMILY_WEIGHTS[_family(archetype)]

    def _blend(disc_: float, g_near_: float):
        """Compute the available methods + robust blended fair value at a given discount rate
        and near-term growth. Returns (fair|None, methods, kept)."""
        g_perp_ = _clamp(min(g_near_, disc_ - 0.035), 0.0, 0.05)
        spread_ = disc_ - g_perp_   # >= 0.035 by construction
        m: dict[str, float] = {}
        # DDM only when the implied dividend yield is plausible (≤13%); an implausibly high
        # dps/price almost always means a bad/special dividend figure (same clamp as fundamentals).
        if dps is not None and dps > 0 and dps / price <= 0.13 and spread_ > 0.01:
            m["ddm"] = _clamp(dps * (1.0 + g_perp_) / spread_, 0.1 * price, 8 * price)
        if bvps is not None and bvps > 0 and roe is not None and spread_ > 0.01:
            jpb = _clamp((roe - g_perp_) / spread_, 0.3, 5.0)
            m["pb"] = _clamp(jpb * bvps, 0.1 * price, 8 * price)
        if eps is not None and eps > 0:
            # normalise a one-off earnings spike so the multiple sits on sustainable earnings
            eps_pe = eps
            sni = [x for x in (series.get("net_income") or []) if isinstance(x, (int, float))]
            if ni is not None and ni > 0 and len(sni) >= 3:
                prior = [x for x in sni if x != ni] or sni
                med_prior = median(prior)
                if med_prior and med_prior > 0 and ni > 1.8 * med_prior:
                    eps_pe = eps * (min(ni, 1.5 * med_prior) / ni)
            base_pe = BASE_PE.get(archetype, DEFAULT_PE)
            tilt = _clamp((g_near_ - 0.04) * 5.0, -0.4, 0.9)
            m["pe"] = _clamp(eps_pe * _clamp(base_pe * (1.0 + tilt), 5.0, 35.0), 0.1 * price, 8 * price)
        if fcf is not None and fcf > 0 and shares and spread_ > 0.01:
            m["fcf"] = _clamp((fcf / shares) * (1.0 + g_perp_) / spread_, 0.1 * price, 8 * price)
        if len(m) < 2:   # need >=2 independent methods to publish
            return None, m, m
        kept_ = dict(m)
        if len(m) >= 3:   # drop outliers (>2.5x / <0.4x the median) so one bad input can't drag it
            med = median(m.values())
            kept_ = {k: v for k, v in m.items() if 0.4 * med <= v <= 2.5 * med} or m
            if len(kept_) < 2:
                kept_ = m
        tot = sum(w.get(k, 0.0) for k in kept_) or 1.0
        f_ = sum(kept_[k] * (w.get(k, 0.0) / tot) for k in kept_)
        if f_ <= 0:
            f_ = sum(kept_.values()) / len(kept_)
        return f_, m, kept_

    fair, methods, kept = _blend(disc, g_near)
    if fair is None:
        return None

    # bull / base / bear range via discount-rate (+/-1pt) & growth (+/-1.5pt) sensitivity
    bear, _, _ = _blend(disc + 0.01, max(0.0, g_near - 0.015))
    bull, _, _ = _blend(max(0.04, disc - 0.01), g_near + 0.015)
    band = [x for x in (bear, fair, bull) if x is not None]
    lo, hi = (min(band), max(band)) if band else (fair, fair)

    upside = fair / price - 1.0
    g = g_near

    vals = list(kept.values())
    dispersion = (max(vals) / min(vals)) if min(vals) > 0 else 9.9
    completeness = sum(x is not None for x in (eps, equity, dps, shares)) + (1 if series.get("years") else 0)
    if len(methods) >= 2 and dispersion < 1.8 and completeness >= 4:
        conf = "high"
    elif len(methods) >= 2 and dispersion < 2.6:
        conf = "medium"
    else:
        conf = "low"

    # extreme upside is usually a data quirk / special situation (low float, one-off earnings),
    # not a clean signal — temper confidence so it drops out of the board & alert filters.
    au = abs(upside)
    if au >= 1.50:
        conf = "low"
    elif au >= 0.80 and conf == "high":
        conf = "medium"

    rating = "undervalued" if upside >= 0.20 else "overvalued" if upside <= -0.20 else "fairly valued"

    # plain-language explanation — deterministic (numbers from code, no LLM)
    driver = max(kept, key=lambda k: w.get(k, 0.0))
    drv = {"ddm": "the dividend-discount model", "pb": "book value vs ROE",
           "pe": "a normalised earnings multiple", "fcf": "discounted cash flow"}[driver]
    summary = (f"Model fair value AED {fair:.2f} is {abs(upside) * 100:.0f}% "
               f"{'above' if upside >= 0 else 'below'} the AED {price:.2f} price — {rating}. "
               f"Driven mainly by {drv}; assumes ~{g * 100:.0f}% growth and a {disc * 100:.1f}% "
               f"discount rate" + (f", {roe * 100:.0f}% ROE" if roe is not None else "") +
               f". {conf.capitalize()} confidence (range AED {lo:.2f}–{hi:.2f}).")

    return {
        "fair_value": round(fair, 3),
        "fair_low": round(lo, 3),
        "fair_high": round(hi, 3),
        "price": round(price, 3),
        "upside_pct": round(upside, 4),
        "rating": rating,
        "confidence": conf,
        "summary": summary,
        "methods": {m: round(v, 3) for m, v in methods.items()},
        "assumptions": {
            "discount_rate": round(disc, 4),
            "growth": round(g, 4),
            "roe": round(roe, 4) if roe is not None else None,
            "eps": round(eps, 4) if eps is not None else None,
            "bvps": round(bvps, 4) if bvps is not None else None,
            "dps": round(dps, 4) if dps is not None else None,
        },
        "method_labels": {
            "ddm": "Dividend discount (Gordon)",
            "pb": "Justified P/B (ROE)",
            "pe": "Earnings multiple",
            "fcf": "FCF perpetuity",
        },
        "basis": "deterministic",
    }
