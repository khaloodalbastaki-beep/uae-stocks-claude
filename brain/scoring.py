"""
Deterministic house-scoring engine: Growth / Stability / Dividend, each 0-100.

Khalid's hard rule (Me.md): "Numbers come from code, never from an LLM. Deterministic
scripts are the authoritative source; LLMs only narrate." So every score here is a
pure function of fundamentals with a fully transparent breakdown — the UI shows the
sub-factors and their contributions, and the AI layer is forbidden from inventing a
score; it may only explain one that this module produced.

Archetype-aware: the blueprint insists "a developer like Emaar is not graded the same
way as a bank." Weights shift per archetype so the same raw metric means different
things for a bank vs a developer vs a utility.

Each pillar returns ScoreResult{ score, grade, subfactors[] } where every subfactor
carries its raw value, normalised 0-100, weight, and a plain-language note. Nothing is
hidden.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


# ---------------------------------------------------------------------------
# Fundamentals input (one record per stock; produced by adapters, tagged w/ source)
# ---------------------------------------------------------------------------
@dataclass
class Fundamentals:
    # growth
    revenue_growth: float = 0.0       # YoY %, e.g. 0.12 = +12%
    profit_growth: float = 0.0        # YoY %
    revenue_cagr_3y: float = 0.0
    margin_trend: float = 0.0         # change in net margin pts YoY, e.g. 0.02 = +2pts
    reinvestment: float = 0.5         # 0..1 capex/expansion intensity (productive)
    catalysts: int = 0                # count of forward growth catalysts (contracts, capacity)
    # stability
    net_debt_to_ebitda: float = 2.0   # leverage (lower better); banks use a different proxy
    current_ratio: float = 1.3        # liquidity (banks: set ~ to LCR proxy)
    ocf_consistency: float = 0.7      # 0..1 operating-cash-flow positivity/stability
    price_volatility: float = 0.30    # annualised vol (lower better)
    governance_cadence: float = 0.7   # 0..1 regular board/AGM/disclosure rhythm
    disclosure_quality: float = 0.7   # 0..1 timeliness + completeness
    macro_sensitivity: float = 0.5    # 0..1 dependence on commodity/macro swings (higher worse)
    # dividend
    dividend_yield: float = 0.0       # decimal, e.g. 0.0528 = 5.28%
    payout_ratio: float = 0.5         # decimal of earnings
    fcf_coverage: float = 1.2         # FCF / dividends (>=1 covered)
    net_debt_pressure: float = 0.3    # 0..1 (higher = more debt strain on payout)
    cut_history: int = 0              # # of dividend cuts/misses in last ~5y
    frequency: str = "annual"         # none|annual|semi|quarterly
    years_paid: int = 3               # consecutive years paying

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SubFactor:
    key: str
    label: str
    raw: float | str
    points: float        # normalised 0..100 for this factor
    weight: float        # 0..1 weight within the pillar
    note: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["contribution"] = round(self.points * self.weight, 1)
        return d


@dataclass
class ScoreResult:
    pillar: str
    score: int           # 0..100
    grade: str           # A+ .. D
    subfactors: list[SubFactor] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pillar": self.pillar,
            "score": self.score,
            "grade": self.grade,
            "subfactors": [s.to_dict() for s in self.subfactors],
        }


# ---------------------------------------------------------------------------
# Normalisation helpers (transparent piecewise-linear)
# ---------------------------------------------------------------------------
def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _lin(x: float, lo: float, hi: float) -> float:
    """Map x in [lo,hi] -> [0,100], clamped. Higher x => higher score."""
    if hi == lo:
        return 50.0
    return _clamp((x - lo) / (hi - lo) * 100.0)


def _lin_inv(x: float, lo: float, hi: float) -> float:
    """Lower x => higher score."""
    return 100.0 - _lin(x, lo, hi)


def _grade(score: int) -> str:
    return ("A+" if score >= 90 else "A" if score >= 80 else "B+" if score >= 72
            else "B" if score >= 64 else "C+" if score >= 56 else "C" if score >= 48
            else "D+" if score >= 40 else "D")


def _combine(pillar: str, subs: list[SubFactor]) -> ScoreResult:
    total_w = sum(s.weight for s in subs) or 1.0
    score = round(sum(s.points * s.weight for s in subs) / total_w)
    score = int(_clamp(score))
    return ScoreResult(pillar=pillar, score=score, grade=_grade(score), subfactors=subs)


# Per-archetype weight overrides. Defaults below; archetypes tweak emphasis.
_DEFAULT_GROWTH_W = {"rev": .26, "profit": .24, "cagr": .16, "margin": .14, "reinvest": .10, "catalysts": .10}
_DEFAULT_STAB_W = {"lev": .22, "liq": .14, "ocf": .18, "vol": .14, "gov": .12, "disc": .10, "macro": .10}
_DEFAULT_DIV_W = {"yield": .18, "payout": .20, "fcf": .22, "debt": .14, "cuts": .16, "freq": .10}

_ARCHETYPE_TWEAKS = {
    # banks: leverage ratio is structural -> downweight; cashflow + governance matter more
    "bank":      {"stab": {"lev": .08, "ocf": .24, "gov": .18, "macro": .16}},
    "developer": {"growth": {"catalysts": .18, "rev": .22}, "stab": {"macro": .18, "lev": .24}},
    "utility":   {"growth": {"rev": .20, "catalysts": .06}, "div": {"fcf": .26, "yield": .20}},
    "toll":      {"div": {"fcf": .24, "yield": .20}, "stab": {"ocf": .22}},
}


def _weights(base: dict, archetype: str, pillar_key: str) -> dict:
    w = dict(base)
    tw = _ARCHETYPE_TWEAKS.get(archetype, {}).get(pillar_key)
    if tw:
        w.update(tw)
    return w


# ---------------------------------------------------------------------------
# Pillars
# ---------------------------------------------------------------------------
def growth_score(f: Fundamentals, archetype: str = "holding") -> ScoreResult:
    w = _weights(_DEFAULT_GROWTH_W, archetype, "growth")
    subs = [
        SubFactor("rev", "Revenue growth (YoY)", round(f.revenue_growth, 4),
                  _lin(f.revenue_growth, -0.05, 0.25), w["rev"],
                  f"{f.revenue_growth*100:.1f}% top-line growth"),
        SubFactor("profit", "Earnings growth (YoY)", round(f.profit_growth, 4),
                  _lin(f.profit_growth, -0.10, 0.30), w["profit"],
                  f"{f.profit_growth*100:.1f}% earnings growth"),
        SubFactor("cagr", "Revenue CAGR (3y)", round(f.revenue_cagr_3y, 4),
                  _lin(f.revenue_cagr_3y, 0.0, 0.20), w["cagr"],
                  f"{f.revenue_cagr_3y*100:.1f}% 3-year CAGR"),
        SubFactor("margin", "Margin direction", round(f.margin_trend, 4),
                  _lin(f.margin_trend, -0.03, 0.04), w["margin"],
                  ("expanding" if f.margin_trend > 0 else "compressing") + " margins"),
        SubFactor("reinvest", "Reinvestment / capex productivity", round(f.reinvestment, 2),
                  _lin(f.reinvestment, 0.2, 0.9), w["reinvest"],
                  "capital being put to work" if f.reinvestment > 0.5 else "light reinvestment"),
        SubFactor("catalysts", "Forward catalysts", f.catalysts,
                  _lin(f.catalysts, 0, 4), w["catalysts"],
                  f"{f.catalysts} identified growth catalyst(s)"),
    ]
    return _combine("growth", subs)


def stability_score(f: Fundamentals, archetype: str = "holding") -> ScoreResult:
    w = _weights(_DEFAULT_STAB_W, archetype, "stab")
    subs = [
        SubFactor("lev", "Leverage (net debt / EBITDA)", round(f.net_debt_to_ebitda, 2),
                  _lin_inv(f.net_debt_to_ebitda, 0.5, 5.0), w["lev"],
                  "conservative balance sheet" if f.net_debt_to_ebitda < 2 else "leveraged"),
        SubFactor("liq", "Liquidity (current ratio)", round(f.current_ratio, 2),
                  _lin(f.current_ratio, 0.8, 2.2), w["liq"],
                  "comfortable liquidity" if f.current_ratio > 1.2 else "tight liquidity"),
        SubFactor("ocf", "Operating cash-flow consistency", round(f.ocf_consistency, 2),
                  _lin(f.ocf_consistency, 0.3, 1.0), w["ocf"],
                  "steady cash generation" if f.ocf_consistency > 0.7 else "lumpy cash flow"),
        SubFactor("vol", "Price volatility (annualised)", round(f.price_volatility, 3),
                  _lin_inv(f.price_volatility, 0.12, 0.55), w["vol"],
                  "low volatility" if f.price_volatility < 0.25 else "volatile"),
        SubFactor("gov", "Governance cadence", round(f.governance_cadence, 2),
                  _lin(f.governance_cadence, 0.3, 1.0), w["gov"],
                  "regular board/AGM rhythm" if f.governance_cadence > 0.6 else "irregular cadence"),
        SubFactor("disc", "Disclosure quality", round(f.disclosure_quality, 2),
                  _lin(f.disclosure_quality, 0.3, 1.0), w["disc"],
                  "timely + complete" if f.disclosure_quality > 0.6 else "patchy disclosure"),
        SubFactor("macro", "Macro / commodity sensitivity", round(f.macro_sensitivity, 2),
                  _lin_inv(f.macro_sensitivity, 0.1, 0.9), w["macro"],
                  "macro-insulated" if f.macro_sensitivity < 0.4 else "macro-exposed"),
    ]
    return _combine("stability", subs)


def dividend_score(f: Fundamentals, archetype: str = "holding") -> ScoreResult:
    w = _weights(_DEFAULT_DIV_W, archetype, "div")
    freq_pts = {"none": 0, "annual": 55, "semi": 75, "quarterly": 92}.get(f.frequency, 40)
    # A high yield is NOT automatically good (blueprint). We reward moderate, covered yields
    # and *penalise* a suspiciously high yield that signals stress.
    if f.dividend_yield <= 0:
        yield_pts = 0.0
    elif f.dividend_yield <= 0.06:
        yield_pts = _lin(f.dividend_yield, 0.0, 0.06)        # 0..100 up to 6%
    else:
        yield_pts = _clamp(100 - (f.dividend_yield - 0.06) * 600)  # decay above 6% (yield trap risk)
    subs = [
        SubFactor("yield", "Yield (quality-adjusted)", round(f.dividend_yield, 4),
                  yield_pts, w["yield"],
                  f"{f.dividend_yield*100:.2f}% yield" + (" — high, check sustainability" if f.dividend_yield > 0.08 else "")),
        SubFactor("payout", "Payout ratio", round(f.payout_ratio, 2),
                  # sweet spot ~35-70%; too low = stingy, too high = stretched
                  _clamp(100 - abs(f.payout_ratio - 0.52) * 170), w["payout"],
                  f"{f.payout_ratio*100:.0f}% of earnings paid out"),
        SubFactor("fcf", "Free-cash-flow coverage", round(f.fcf_coverage, 2),
                  _lin(f.fcf_coverage, 0.6, 2.0), w["fcf"],
                  "comfortably covered" if f.fcf_coverage >= 1.2 else "thin / uncovered coverage"),
        SubFactor("debt", "Debt pressure on payout", round(f.net_debt_pressure, 2),
                  _lin_inv(f.net_debt_pressure, 0.1, 0.9), w["debt"],
                  "low debt strain" if f.net_debt_pressure < 0.4 else "debt may pressure payout"),
        SubFactor("cuts", "Cut / miss history", f.cut_history,
                  _lin_inv(f.cut_history, 0, 3), w["cuts"],
                  "clean payment record" if f.cut_history == 0 else f"{f.cut_history} cut(s)/miss(es) recently"),
        SubFactor("freq", "Frequency & regularity", f.frequency,
                  float(freq_pts), w["freq"],
                  f"{f.frequency} distribution, {f.years_paid}y streak"),
    ]
    return _combine("dividend", subs)


def score_all(f: Fundamentals, archetype: str = "holding") -> dict:
    """Returns the three pillars + a blended headline, fully broken down."""
    g = growth_score(f, archetype)
    s = stability_score(f, archetype)
    d = dividend_score(f, archetype)
    # headline is a context-light blend; UI shows the three pillars separately
    headline = round((g.score * 0.4 + s.score * 0.35 + d.score * 0.25))
    return {
        "growth": g.to_dict(),
        "stability": s.to_dict(),
        "dividend": d.to_dict(),
        "headline": int(_clamp(headline)),
        "headline_grade": _grade(int(_clamp(headline))),
        "archetype": archetype,
        "engine": "deterministic-v1",
    }
