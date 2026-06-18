"""
Narration: turn structured facts into investor-friendly text.

The hard line (Me.md): the LLM NEVER produces a number or the headline call. Here:
  * House scores come from brain.scoring (deterministic).
  * The AI stance/confidence come from compute_signals() below — deterministic thresholds
    over momentum, events, and the house scores.
  * The provider (claude CLI / OpenAI / stub) only writes the *prose* — reasons, risks,
    why-it-matters, summaries — and is explicitly told the stance is fixed.

So if you turn the AI provider off entirely, every figure and every call is identical;
you just get template prose instead of model prose. That is the whole point.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .provider import get_provider
from .schemas import DISCLOSURE_SCHEMA, ANALYSIS_SCHEMA
from ..adapters.base import Disclosure, SOURCE_AI, DQ_DELAYED, Provenance

UTC = timezone.utc


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Disclosure enrichment
# ---------------------------------------------------------------------------
_WHY = {
    "results": "Earnings set the near-term tone and feed directly into the dividend and growth picture.",
    "board_meeting": "Board meetings in the UAE often precede price-sensitive decisions (dividends, capital, buybacks).",
    "agm_invitation": "The AGM is where dividends and board changes are formally approved.",
    "agm_resolution": "Resolutions confirm or change capital, dividend and governance outcomes.",
    "dividend": "Dividend actions are a primary driver of total return for UAE income investors.",
    "acquisition": "M&A can re-rate the growth and risk profile materially.",
    "capital_raise": "New capital changes the balance sheet, dilution and funding outlook.",
    "governance": "Leadership/board changes affect strategy continuity and disclosure quality.",
    "subsidiary": "Subsidiary developments can be material to the consolidated group.",
    "other": "Context for the broader investment case.",
}


def enrich_disclosure(d: Disclosure, provider=None) -> Disclosure:
    """Fill AI fields. Keeps existing template values as the deterministic fallback."""
    provider = provider or get_provider()
    # deterministic baseline already on the object (from the adapter); set a why-line
    if not d.why_it_matters:
        d.why_it_matters = _WHY.get(d.event_type, _WHY["other"])
    if not d.summary_en:
        d.summary_en = f"{d.title_en}. {d.body_excerpt}".strip()
    if not d.summary_ar and d.title_lang == "ar":
        d.summary_ar = d.title_src

    out = provider.complete_json(
        system=("You classify and summarise a UAE-listed company disclosure for retail "
                "investors. Be concise, factual, neutral. Do NOT give investment advice. "
                "Preserve any Arabic meaning faithfully."),
        user=(f"Company disclosure:\nType hint: {d.event_type}\n"
              f"Original title ({d.title_lang}): {d.title_src}\n"
              f"English title: {d.title_en}\nExcerpt: {d.body_excerpt}"),
        schema=DISCLOSURE_SCHEMA,
    )
    if out:
        d.event_type = out.get("event_type", d.event_type)
        d.summary_en = out.get("summary_en", d.summary_en)
        d.summary_ar = out.get("summary_ar", d.summary_ar)
        d.why_it_matters = out.get("why_it_matters", d.why_it_matters)
        d.materiality = int(out.get("materiality", d.materiality))
        d.sentiment = out.get("sentiment", d.sentiment)
        d.linked_entities = out.get("linked_entities", d.linked_entities)
        # mark that an AI lane touched the derived fields
        d.prov = Provenance(SOURCE_AI, f"App AI ({provider.name})", DQ_DELAYED, _now_iso(),
                            lang=d.title_lang)
    return d


# ---------------------------------------------------------------------------
# AI Analyze This Stock — deterministic stance, narrated prose
# ---------------------------------------------------------------------------
def _stance_from(score: float) -> str:
    return "Bullish" if score >= 66 else "Cautious" if score <= 42 else "Neutral"


def _conf_from(spread: float) -> str:
    # spread = how strong/clean the signal is (0..100)
    return "high" if spread >= 24 else "medium" if spread >= 12 else "low"


def compute_signals(quote, scores: dict, fundamentals, disclosures: list, events_pressure: float = 0.0) -> dict:
    """Deterministic short- and long-horizon signal. Pure function of facts."""
    g = scores["growth"]["score"]
    s = scores["stability"]["score"]
    dv = scores["dividend"]["score"]

    # --- short term: momentum + disclosure novelty + event pressure ---
    chg = (quote.change_pct if quote else 0.0) * 100.0
    recent_mat = 0
    recent_senti = 0.0
    for d in disclosures[:5]:
        recent_mat = max(recent_mat, d.materiality)
        recent_senti += {"positive": 1, "neutral": 0, "cautious": -0.5, "negative": -1}.get(d.sentiment, 0)
    st_raw = 50 + chg * 3 + recent_senti * 4 + (recent_mat - 50) * 0.12 + events_pressure
    st_raw = max(0, min(100, st_raw))
    st_spread = abs(st_raw - 50) + (recent_mat * 0.15)

    # --- long term: house scores blend ---
    lt_raw = g * 0.42 + s * 0.36 + dv * 0.22
    lt_spread = abs(lt_raw - 50)

    short_reasons, short_risks = [], []
    if chg > 0.8:
        short_reasons.append(f"Positive price momentum (+{chg:.1f}% on the session in demo data)")
    elif chg < -0.8:
        short_risks.append(f"Negative price momentum ({chg:.1f}% on the session in demo data)")
    if recent_mat >= 70:
        short_reasons.append(f"A high-materiality disclosure ({recent_mat}/100) is in the recent flow")
    if recent_senti > 0:
        short_reasons.append("Recent disclosure tone skews positive")
    elif recent_senti < 0:
        short_risks.append("Recent disclosure tone skews cautious/negative")
    if not short_reasons:
        short_reasons.append("No strong short-term catalysts; trading on broad market drift")
    if not short_risks:
        short_risks.append("A surprise filing or a sector-wide move could shift the picture quickly")

    long_reasons, long_risks = [], []
    if g >= 62:
        long_reasons.append(f"Solid growth profile (Growth {g}/100)")
    if s >= 62:
        long_reasons.append(f"Resilient balance sheet / stability (Stability {s}/100)")
    if dv >= 62:
        long_reasons.append(f"Dependable dividend characteristics (Dividend {dv}/100)")
    if g < 45:
        long_risks.append(f"Weak growth signal (Growth {g}/100)")
    if s < 45:
        long_risks.append(f"Balance-sheet / stability concerns (Stability {s}/100)")
    if fundamentals and fundamentals.macro_sensitivity > 0.65:
        long_risks.append("High sensitivity to commodity / macro swings")
    if not long_reasons:
        long_reasons.append("Mixed fundamentals; no single pillar stands out")
    if not long_risks:
        long_risks.append("Execution and macro conditions remain the key swing factors")

    return {
        "short": {"stance": _stance_from(st_raw), "confidence": _conf_from(st_spread),
                  "score": round(st_raw, 1), "reasons": short_reasons[:5], "risks": short_risks[:5]},
        "long": {"stance": _stance_from(lt_raw), "confidence": _conf_from(lt_spread),
                 "score": round(lt_raw, 1), "reasons": long_reasons[:5], "risks": long_risks[:5]},
    }


def analyze_stock(sec, quote, scores, fundamentals, disclosures, provider=None) -> dict:
    """Returns ANALYSIS_SCHEMA-shaped output. Stance/confidence are deterministic; the
    provider only rewrites the prose around the fixed signal."""
    provider = provider or get_provider()
    sig = compute_signals(quote, scores, fundamentals, disclosures)

    base = {
        "short_term": {
            "stance": sig["short"]["stance"], "confidence": sig["short"]["confidence"],
            "reasons": sig["short"]["reasons"], "risks": sig["short"]["risks"],
            "what_would_change_view": "A new high-materiality disclosure, an unexpected sector move, or a sharp commodity shock in this name's exposure map.",
        },
        "long_term": {
            "stance": sig["long"]["stance"], "confidence": sig["long"]["confidence"],
            "reasons": sig["long"]["reasons"], "risks": sig["long"]["risks"],
            "what_would_change_view": "A durable change in the growth, stability or dividend pillars — e.g. a re-rating in earnings, a leverage spike, or a dividend cut.",
        },
        "_signal": sig,
        "_engine": "deterministic-signal+narration",
        "provider": provider.name,
        "generated_at": _now_iso(),
    }

    # let the LLM lane improve only the prose, with stance FIXED
    out = provider.complete_json(
        system=("You are a transparent equity research assistant for UAE stocks. The STANCE "
                "and CONFIDENCE are FIXED inputs — do not change them. Rewrite the reasons, "
                "risks and 'what would change the view' to be clear and specific for a retail "
                "investor. This is research support, NOT personalised investment advice."),
        user=(f"Company: {sec.name_en} ({sec.symbol}, {sec.exchange}, {sec.sector})\n"
              f"Fixed short-term stance: {sig['short']['stance']} ({sig['short']['confidence']})\n"
              f"Fixed long-term stance: {sig['long']['stance']} ({sig['long']['confidence']})\n"
              f"House scores: Growth {scores['growth']['score']}, Stability {scores['stability']['score']}, "
              f"Dividend {scores['dividend']['score']}\n"
              f"Deterministic short reasons: {sig['short']['reasons']}\n"
              f"Deterministic long reasons: {sig['long']['reasons']}"),
        schema=ANALYSIS_SCHEMA,
    )
    if out and isinstance(out, dict):
        for horizon in ("short_term", "long_term"):
            h = out.get(horizon, {})
            # keep deterministic stance/confidence; take model prose if present
            if h.get("reasons"):
                base[horizon]["reasons"] = h["reasons"][:5]
            if h.get("risks"):
                base[horizon]["risks"] = h["risks"][:5]
            if h.get("what_would_change_view"):
                base[horizon]["what_would_change_view"] = h["what_would_change_view"]
    return base
