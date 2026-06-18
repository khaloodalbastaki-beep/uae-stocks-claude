"""
Mizan (ميزان, "balance/scales") — the UAE fundamentals agent.

Job: for each UAE-listed company, transcribe the latest REPORTED financials from
authoritative sources into data/fundamentals/<SYMBOL>.json. The deterministic brain
(FundamentalsStore + scoring) turns those reported numbers into the house scores — Mizan
never computes a score, it only extracts what the company reported, with a source URL +
date + confidence. Honest-degraded: if it can't source revenue + net income, it writes
nothing for that symbol (the brain keeps the modeled estimate, clearly labelled).

Free cloud LLM lane (no Claude-Max quota burn): MIZAN_PROVIDER=gemini (grounded via Google
Search, recommended) | groq | openrouter. Key in agents/mizan/.env.

Usage:
    python3 agents/mizan/mizan.py --symbols FAB,EMAAR     # specific names
    python3 agents/mizan/mizan.py --all                   # whole registry
    python3 agents/mizan/mizan.py --bus                   # process _Bus/inbox/mizan/ requests
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# load agents/mizan/.env if present (simple KEY=VALUE)
_envf = Path(__file__).resolve().parent / ".env"
if _envf.exists():
    for line in _envf.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from agents.mizan import llm  # noqa: E402
from brain.registry import load_universe, by_symbol  # noqa: E402

DATA = ROOT / "data" / "fundamentals"
UTC = timezone.utc

SYSTEM = (
    "You are Mizan, a meticulous financial-data extraction analyst for UAE-listed equities. "
    "You transcribe REPORTED figures from authoritative sources (company annual report / IR "
    "page, ADX/DFM filing, or reputable financial press like Reuters/Bloomberg/Zawya/Argaam). "
    "You NEVER invent or estimate a number — if you cannot verify a figure from a real source, "
    "you return null for it. Report all monetary figures in AED (convert USD at ~3.6725). "
    "Respond with a SINGLE JSON object and nothing else."
)

SCHEMA_HINT = (
    '{"symbol":"<SYM>","found":<bool>,"as_of":"<FY2024|2024-12-31|null>","currency":"AED",'
    '"source":"<short source name>","source_url":"<url|null>","confidence":"high|medium|low",'
    '"reported":{"revenue":<n|null>,"revenue_prior":<n|null>,"net_income":<n|null>,'
    '"net_income_prior":<n|null>,"net_margin":<0..1|null>,"net_margin_prior":<0..1|null>,'
    '"total_debt":<n|null>,"ebitda":<n|null>,"operating_cash_flow":<n|null>,'
    '"current_ratio":<n|null>,"dividend_per_share":<n|null>,"payout_ratio":<0..1|null>,'
    '"fcf":<n|null>,"cut_history_5y":<int|null>,"dividend_frequency":"annual|semi|quarterly|none|null",'
    '"years_paid":<int|null>}}'
)


def _iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _existing_source_url(symbol: str) -> str | None:
    """The source_url from a prior fundamentals record, so `web` mode re-grounds from the
    company's known filing/IR page when refreshing."""
    f = DATA / f"{symbol}.json"
    if f.exists():
        try:
            return (json.loads(f.read_text()) or {}).get("source_url")
        except Exception:
            return None
    return None


def extract(symbol: str) -> dict | None:
    sec = by_symbol(symbol)
    if not sec:
        print(f"[mizan] unknown symbol {symbol}")
        return None
    exch = "Abu Dhabi (ADX)" if sec.exchange == "ADX" else "Dubai (DFM)"
    base_q = (
        f"Company: {sec.name_en} (ticker {symbol}, listed on {exch}).\n"
        f"Find its MOST RECENT full-year reported financials (FY2024 preferred, else latest). "
        f"Include the PRIOR year's revenue and net income (for growth). For banks, use total "
        f"operating income as 'revenue' and leave total_debt/ebitda null."
    )
    # HYBRID grounding modes (MIZAN_FETCH_PROVIDER):
    #   web    — Gemini-free: fetch the real filing/IR page + Wikipedia ourselves (headless
    #            Chromium + urllib), then the main provider (gpt-oss:120b) extracts from it.
    #   gemini — grounded via Google Search, then the main provider extracts.
    # Either way the strong extractor only transcribes what's in the fetched text.
    fetch_prov = os.environ.get("MIZAN_FETCH_PROVIDER", "").lower()
    main_prov = os.environ.get("MIZAN_PROVIDER", "gemini").lower()
    if fetch_prov == "web":
        from agents.mizan import fetch
        prior = _existing_source_url(symbol)
        src = fetch.gather_text(sec.name_en, prior)
        if not src:
            print(f"[mizan] {symbol}: web fetch returned nothing; kept modeled")
            return None
        out = llm.complete_with(main_prov, SYSTEM,
                                f"From this SOURCE TEXT (a real filing/IR page + Wikipedia), extract the figures. "
                                f"Use ONLY numbers present in the text; AED (convert USD ~3.6725); for banks use "
                                f"total operating income as revenue.\n\nSOURCE TEXT:\n{src}\n\n"
                                f"Return ONLY this JSON (null for anything not in the text; found=false if no "
                                f"revenue+net_income in the text):\n{SCHEMA_HINT}",
                                grounded=False)
    elif fetch_prov and fetch_prov != main_prov:
        src = llm.text(fetch_prov,
                       "You are a financial-data researcher. Find real, sourced figures only; cite the source URL and fiscal period.",
                       base_q + "\nList every reported figure you can verify, with the source URL and the fiscal period. Plain text.",
                       grounded=True)
        if not src:
            print(f"[mizan] {symbol}: hybrid fetch returned nothing; falling back to single-call")
            out = llm.complete(SYSTEM, base_q + f"\nReturn ONLY:\n{SCHEMA_HINT}", grounded=True)
        else:
            out = llm.complete_with(main_prov, SYSTEM,
                                    f"From these SOURCED findings, extract the figures.\n\nFINDINGS:\n{src}\n\n"
                                    f"Return ONLY this JSON (null for anything not in the findings; found=false if no revenue+net_income):\n{SCHEMA_HINT}",
                                    grounded=False)
    else:
        out = llm.complete(SYSTEM, base_q + f"\nReturn ONLY this JSON shape (null for anything "
                           f"unverifiable; found=false if you cannot source revenue AND net_income):\n{SCHEMA_HINT}",
                           grounded=True)
    if not out or not isinstance(out, dict):
        print(f"[mizan] {symbol}: no/invalid LLM output")
        return None
    rep = out.get("reported") or {}
    if not out.get("found") or rep.get("revenue") is None or rep.get("net_income") is None:
        print(f"[mizan] {symbol}: not found / insufficient (kept modeled)")
        return None
    rec = {
        "symbol": symbol,
        "as_of": out.get("as_of"),
        "currency": out.get("currency", "AED"),
        "source": out.get("source", "Mizan extraction"),
        "source_url": out.get("source_url"),
        "extractor": f"mizan/{os.environ.get('MIZAN_PROVIDER', 'gemini')}",
        "confidence": out.get("confidence", "medium"),
        "retrieved_at": _iso(),
        "reported": rep,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"{symbol}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    print(f"[mizan] {symbol}: wrote fundamentals ({out.get('confidence')}, {out.get('as_of')})")
    return rec


def run_symbols(symbols: list[str]) -> int:
    n = 0
    for s in symbols:
        sym = s.strip().upper()
        ok = extract(sym)
        _record_attempt(sym)   # mark touched even on a miss, so we don't retry it next run
        if ok:
            n += 1
    print(f"[mizan] done: {n}/{len(symbols)} real fundamentals written -> {DATA}")
    return n


# ── staleness rotation: refresh only the oldest N, skip anything touched recently ──
def _attempts_path() -> Path:
    return DATA / ".attempts.json"


def _load_attempts() -> dict:
    p = _attempts_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def _record_attempt(symbol: str) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    a = _load_attempts()
    a[symbol] = _iso()
    _attempts_path().write_text(json.dumps(a))


def _last_touched(symbol: str, attempts: dict) -> str | None:
    """Most recent of: successful record's retrieved_at OR last attempt. None = never touched."""
    times = []
    rec = DATA / f"{symbol}.json"
    if rec.exists():
        try:
            t = json.loads(rec.read_text()).get("retrieved_at")
            if t:
                times.append(t)
        except Exception:
            pass
    if attempts.get(symbol):
        times.append(attempts[symbol])
    return max(times) if times else None


def run_stale(n: int) -> int:
    """Refresh the N stalest names whose last touch is older than MIZAN_MIN_AGE_HOURS
    (default 20h) — or never touched. Skips the freshly-updated/attempted ones, so an
    hourly schedule rotates through the universe without repeating the newest."""
    from datetime import timedelta
    min_age = float(os.environ.get("MIZAN_MIN_AGE_HOURS", "20"))
    cutoff = datetime.now(UTC) - timedelta(hours=min_age)
    attempts = _load_attempts()
    cands = []  # (sort_key, symbol) — never-touched sort oldest (epoch 0)
    for s in load_universe():
        t = _last_touched(s.symbol, attempts)
        if t is None:
            cands.append(("", s.symbol))            # never touched → highest priority
        else:
            try:
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            except Exception:
                dt = cutoff - timedelta(days=1)
            if dt < cutoff:
                cands.append((t, s.symbol))          # stale enough → eligible
    cands.sort(key=lambda x: x[0])                   # oldest / never-touched first
    batch = [sym for _, sym in cands[:max(1, n)]]
    if not batch:
        print(f"[mizan] nothing stale (all touched within {min_age:.0f}h) — skip")
        return 0
    print(f"[mizan] stale batch ({len(batch)} of {len(cands)} eligible): {', '.join(batch)}")
    return run_symbols(batch)


def run_bus() -> None:
    """Process Hermes requests dropped in _Bus/inbox/mizan/ (vault). Each open request may
    name symbols in its Task; Mizan extracts them and fills the Response."""
    inbox = Path("/Volumes/Samsung_SSD_970_EVO_Plus_Media/Khalid OS/_Bus/inbox/mizan")
    if not inbox.exists():
        print("[mizan] no bus inbox found"); return
    import re
    for msg in sorted(inbox.glob("*.md")):
        txt = msg.read_text()
        if "status: open" not in txt and "status: claimed" not in txt:
            continue
        syms = re.findall(r"\b([A-Z0-9]{2,12})\b", txt.split("## Task", 1)[-1])
        known = {s.symbol for s in load_universe()}
        targets = [s for s in dict.fromkeys(syms) if s in known] or list(known)
        n = run_symbols(targets[:60])
        resp = txt.replace("status: open", "status: done").replace("status: claimed", "status: done")
        if "## Response" in resp:
            resp = resp.split("## Response")[0] + f"## Response\nMizan wrote real fundamentals for {n} symbol(s) at {_iso()}.\n"
        msg.write_text(resp)
        print(f"[mizan] bus message handled: {msg.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Mizan — UAE fundamentals extraction agent")
    ap.add_argument("--symbols", type=str, help="comma-separated symbols")
    ap.add_argument("--all", action="store_true", help="whole registry")
    ap.add_argument("--stale", type=int, metavar="N", help="refresh the N stalest names (skips recently-touched; for the hourly schedule)")
    ap.add_argument("--bus", action="store_true", help="process _Bus/inbox/mizan/ requests")
    args = ap.parse_args()
    if args.bus:
        run_bus()
    elif args.stale is not None:
        run_stale(args.stale)
    elif args.all:
        run_symbols([s.symbol for s in load_universe()])
    elif args.symbols:
        run_symbols(args.symbols.split(","))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
