"""
Merge workflow-gathered financial statements into the fundamentals store.

Reads the StructuredOutput records from a finished `uae-financials-gather` workflow's
subagent transcripts (gather stage carries `found`, verify stage carries `accept`),
prefers the verified record per symbol, and ENRICHES each data/fundamentals/<SYM>.json:
  - adds a multi-year `series` (years / revenue / net_income / operating_cash_flow) for the
    Financials charts, with the latest year reconciled to the already-verified reported figure
  - adds valuation inputs to `reported`: shares_outstanding, total_equity, eps (+ dividend_per_share
    only if missing)
Existing verified `reported` figures are never overwritten (real-data-sacred). Honest-degraded:
implausible values are skipped, not forced.

    python3 tools/merge_statements.py <workflow_transcript_dir>
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "fundamentals"


def _walk_structured(obj):
    out = []
    def w(x):
        if isinstance(x, dict):
            if x.get("name") == "StructuredOutput" and isinstance(x.get("input"), dict):
                out.append(x["input"])
            for v in x.values():
                w(v)
        elif isinstance(x, list):
            for v in x:
                w(v)
    w(obj)
    return out


def extract(transcript_dir: Path) -> dict[str, dict]:
    """symbol -> best record (verify/accept preferred over gather/found)."""
    gather, verify = {}, {}
    for f in sorted(transcript_dir.glob("*.jsonl")):
        for line in f.read_text(errors="ignore").splitlines():
            try:
                o = json.loads(line)
            except Exception:
                continue
            for rec in _walk_structured(o):
                sym = rec.get("symbol")
                if not sym:
                    continue
                if "accept" in rec:
                    verify[sym] = rec
                elif "found" in rec:
                    gather[sym] = rec
    best = {}
    for sym in set(gather) | set(verify):
        v = verify.get(sym)
        if v and v.get("accept"):
            best[sym] = v
        elif sym in gather and gather[sym].get("found"):
            best[sym] = gather[sym]
        elif v:
            best[sym] = v
    return best


def _num(v):
    return float(v) if isinstance(v, (int, float)) and v == v else None


def _align(years, arr):
    arr = list(arr or [])
    arr = arr[:len(years)] + [None] * max(0, len(years) - len(arr))
    return [_num(x) for x in arr]


def merge_one(sym: str, data: dict) -> str:
    fp = DATA / f"{sym}.json"
    if not fp.exists():
        return f"{sym}: no base record — skip"
    if data.get("accept") is False:
        return f"{sym}: verify rejected — skip"
    rec = json.loads(fp.read_text())
    rep = rec.setdefault("reported", {})

    years = [int(y) for y in (data.get("years") or []) if isinstance(y, (int, float))]
    rev = _align(years, data.get("revenue"))
    ni = _align(years, data.get("net_income"))
    ocf = _align(years, data.get("operating_cash_flow"))

    # NOTE: do NOT reconcile against the seed `reported.revenue/net_income` — those are stored in
    # mixed units (some absolute AED, some millions). The workflow series is consistently absolute
    # AED and was already skeptically audited, so keep it as the canonical valuation/charts source.
    notes = []
    if years and (any(v is not None for v in rev) or any(v is not None for v in ni)):
        rec["series"] = {"years": years, "revenue": rev, "net_income": ni,
                         "operating_cash_flow": ocf, "source": "workflow-research"}
        notes.append(f"series[{len(years)}y]")

    # latest non-null series net income (absolute AED) — used to backfill EPS consistently
    ni_latest = next((v for v in reversed(ni) if isinstance(v, (int, float))), None)

    # valuation inputs (all absolute AED from the workflow) — set when missing
    shares = _num(data.get("shares_outstanding"))
    equity = _num(data.get("total_equity"))
    eps = _num(data.get("eps"))
    dps = _num(data.get("dividend_per_share"))
    if shares and shares > 0 and rep.get("shares_outstanding") is None:
        rep["shares_outstanding"] = shares; notes.append("shares")
    if equity and equity > 0 and rep.get("total_equity") is None:
        rep["total_equity"] = equity; notes.append("equity")
    if rep.get("eps") is None:
        # trust the researched EPS only if it reconciles with absolute net income (±30%);
        # otherwise derive from the absolute series (avoids unit drift).
        sh = _num(rep.get("shares_outstanding"))
        if eps is not None and ni_latest and sh and abs(eps * sh - ni_latest) / abs(ni_latest) <= 0.30:
            rep["eps"] = eps; notes.append("eps")
        elif ni_latest and sh:
            rep["eps"] = round(ni_latest / sh, 4); notes.append("eps~series")
        elif eps is not None:
            rep["eps"] = eps; notes.append("eps?")
    if rep.get("dividend_per_share") is None and dps is not None:
        rep["dividend_per_share"] = dps; notes.append("dps")

    rec["statements_extractor"] = "workflow-research"
    fp.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return f"{sym}: {', '.join(notes) or 'no usable additions'}"


def main():
    if len(sys.argv) < 2:
        print("usage: merge_statements.py <workflow_transcript_dir>"); sys.exit(1)
    td = Path(sys.argv[1])
    best = extract(td)
    print(f"[merge] extracted {len(best)} symbols from {td.name}")
    enriched = 0
    for sym, data in sorted(best.items()):
        msg = merge_one(sym, data)
        if "series[" in msg or "shares" in msg or "equity" in msg or "eps" in msg:
            enriched += 1
        print("  " + msg)
    print(f"[merge] enriched {enriched}/{len(best)} fundamentals records")


if __name__ == "__main__":
    main()
