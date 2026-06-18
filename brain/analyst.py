"""
Analyst — fleet role for the `nemotron` CLI agent (NVIDIA Nemotron-3-Ultra, free via Nous).

Job: write the QUALITATIVE prose (reasons / risks / what-would-change) for the AI Analysis
tab, wrapped around the brain's FIXED deterministic stance + confidence. It NEVER changes
the stance and NEVER states specific figures it wasn't given (Khalid's rule: numbers from
code, the LLM only narrates). Output is cached to data/ai/<SYMBOL>.json; the pipeline
overlays it on the next build. Staleness-rotated like Mizan/news so it stays within free
rate limits and never repeats a freshly-narrated name.

    python3 -m brain.analyst --stale 4      # for the hourly schedule
    python3 -m brain.analyst --symbols EMAAR
Agent override: ANALYST_AGENT=nemotron|freeagent|robin
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .registry import load_universe
from .ai.provider import CliAgentProvider

UTC = timezone.utc
ROOT = Path(__file__).resolve().parent.parent
STOCKS = ROOT / "data" / "stocks"
AIDIR = ROOT / "data" / "ai"
AGENT = os.environ.get("ANALYST_AGENT", "nemotron")
# Big free reasoning models (nemotron ~210s on the narration prompt) blow past the
# 90s CLI default — give the Analyst a generous cap, env-overridable.
TIMEOUT = float(os.environ.get("ANALYST_TIMEOUT", "300"))
# If the primary narrator times out / returns nothing, fall back once to a fast flash
# model so the AI tab still gets prose. "" disables the fallback.
BACKUP = os.environ.get("ANALYST_BACKUP_AGENT", "freeagent")

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["short_term", "long_term"],
    "properties": {
        "short_term": {"type": "object", "additionalProperties": False,
                       "required": ["reasons", "risks", "what_would_change_view"],
                       "properties": {"reasons": {"type": "array", "items": {"type": "string"}},
                                      "risks": {"type": "array", "items": {"type": "string"}},
                                      "what_would_change_view": {"type": "string"}}},
        "long_term": {"type": "object", "additionalProperties": False,
                      "required": ["reasons", "risks", "what_would_change_view"],
                      "properties": {"reasons": {"type": "array", "items": {"type": "string"}},
                                     "risks": {"type": "array", "items": {"type": "string"}},
                                     "what_would_change_view": {"type": "string"}}},
    },
}


def _iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def narrate(symbol: str, providers: list[CliAgentProvider]) -> dict | None:
    sf = STOCKS / f"{symbol}.json"
    if not sf.exists():
        print(f"[analyst] {symbol}: no built stock file yet — skip")
        return None
    try:
        s = json.loads(sf.read_text())
    except Exception:
        return None
    a = s.get("ai_analysis", {}) or {}
    sig = a.get("_signal", {}) or {}
    scores = s.get("scores", {}) or {}
    if not sig:
        return None
    sys_p = ("You are a transparent equity research analyst for UAE stocks. The STANCE and "
             "CONFIDENCE are FIXED inputs — never change them. Write clear, qualitative reasons, "
             "risks and a 'what would change the view' line for a retail investor. Do NOT state "
             "specific figures, percentages, prices or dates you were not given — reason from the "
             "house scores and the signal notes. This is research support, NOT advice.")
    user = (f"Company: {s.get('name_en')} ({symbol}, {s.get('exchange')}, {s.get('sector')}).\n"
            f"FIXED short-term stance: {sig['short']['stance']} ({sig['short']['confidence']}).\n"
            f"FIXED long-term stance: {sig['long']['stance']} ({sig['long']['confidence']}).\n"
            f"House scores (0-100): Growth {scores.get('growth',{}).get('score')}, "
            f"Stability {scores.get('stability',{}).get('score')}, Dividend {scores.get('dividend',{}).get('score')}.\n"
            f"Short-signal notes: {sig['short'].get('reasons')} | risks: {sig['short'].get('risks')}\n"
            f"Long-signal notes: {sig['long'].get('reasons')} | risks: {sig['long'].get('risks')}\n"
            f"Return up to 4 reasons and 4 risks per horizon.")
    # Try primary, then fall back to the next provider on timeout/invalid output.
    for prov in providers:
        out = prov.complete_json(sys_p, user, SCHEMA)
        if out and "short_term" in out and "long_term" in out:
            used = prov.agent
            rec = {"symbol": symbol, "narrator": used, "generated_at": _iso(),
                   "short_term": out["short_term"], "long_term": out["long_term"]}
            AIDIR.mkdir(parents=True, exist_ok=True)
            (AIDIR / f"{symbol}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
            print(f"[analyst] {symbol}: narrated by {used}")
            return rec
        print(f"[analyst] {symbol}: no/invalid output from {prov.agent} — trying next" if prov is not providers[-1]
              else f"[analyst] {symbol}: no/invalid output from {prov.agent}")
    return None


def _providers() -> list[CliAgentProvider]:
    provs = [CliAgentProvider(AGENT, timeout=TIMEOUT)]
    if BACKUP and BACKUP != AGENT:
        provs.append(CliAgentProvider(BACKUP, timeout=TIMEOUT))
    return provs


def run_symbols(symbols: list[str]) -> int:
    provs = _providers()
    n = sum(1 for s in symbols if narrate(s.strip().upper(), provs))
    print(f"[analyst] done: {n}/{len(symbols)} narrated ({' -> '.join(p.agent for p in provs)}) -> {AIDIR}")
    return n


def run_stale(n: int) -> int:
    min_age = float(os.environ.get("ANALYST_MIN_AGE_HOURS", "24"))
    cutoff = datetime.now(UTC) - timedelta(hours=min_age)
    cands = []
    for sec in load_universe():
        f = AIDIR / f"{sec.symbol}.json"
        t = None
        if f.exists():
            try:
                t = json.loads(f.read_text()).get("generated_at")
            except Exception:
                t = None
        if t is None:
            cands.append(("", sec.symbol))
        else:
            try:
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            except Exception:
                dt = cutoff - timedelta(days=1)
            if dt < cutoff:
                cands.append((t, sec.symbol))
    cands.sort(key=lambda x: x[0])
    batch = [sym for _, sym in cands[:max(1, n)]]
    if not batch:
        print(f"[analyst] nothing stale (all narrated within {min_age:.0f}h) — skip")
        return 0
    print(f"[analyst] stale batch ({len(batch)} of {len(cands)}): {', '.join(batch)}")
    return run_symbols(batch)


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyst — nemotron writes AI-analysis prose")
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
