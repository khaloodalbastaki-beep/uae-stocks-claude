"""
Roll the fundamentals store to the latest full fiscal year (FY2025) from a finished
`uae-fy2025-refresh` workflow. Unlike merge_statements.py (which only enriched), this UPDATES
the headline `reported` figures to latest_fy and refreshes the series — and in doing so makes
`reported` consistently absolute-AED (the old seed was mixed-unit).

Only accepted records are applied, and only when latest_fy >= the record's current as_of year
(never downgrades). Backs nothing up itself — caller should back up data/fundamentals first.

    python3 tools/merge_fy2025.py <workflow_transcript_dir>
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "fundamentals"


def _walk(obj, out):
    if isinstance(obj, dict):
        if obj.get("name") == "StructuredOutput" and isinstance(obj.get("input"), dict):
            out.append(obj["input"])
        for v in obj.values():
            _walk(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk(v, out)


def extract(td: Path) -> dict[str, dict]:
    gather, verify = {}, {}
    for f in sorted(td.glob("*.jsonl")):
        for line in f.read_text(errors="ignore").splitlines():
            try:
                o = json.loads(line)
            except Exception:
                continue
            recs = []
            _walk(o, recs)
            for r in recs:
                sym = r.get("symbol")
                if not sym:
                    continue
                if "accept" in r:
                    verify[sym] = r
                elif "found" in r:
                    gather[sym] = r
    best = {}
    for sym in set(gather) | set(verify):
        v = verify.get(sym)
        if v and v.get("accept"):
            best[sym] = v
        elif sym in gather and gather[sym].get("found"):
            best[sym] = gather[sym]
    return best


def _num(v):
    return float(v) if isinstance(v, (int, float)) and v == v else None


def _year_of(as_of) -> int | None:
    for tok in str(as_of or "").replace("-", " ").replace("FY", " ").split():
        if tok.isdigit() and len(tok) == 4:
            return int(tok)
    return None


def merge_one(sym: str, data: dict) -> str:
    if data.get("accept") is False:
        return f"{sym}: rejected — skip"
    fp = DATA / f"{sym}.json"
    if not fp.exists():
        return f"{sym}: no base record — skip"
    rec = json.loads(fp.read_text())
    rep = rec.setdefault("reported", {})

    years = [int(y) for y in (data.get("years") or []) if isinstance(y, (int, float))]
    rev = data.get("revenue") or []
    ni = data.get("net_income") or []
    ocf = data.get("operating_cash_flow") or []
    if not years:
        return f"{sym}: no series — skip"
    lf = data.get("latest_fy") or years[-1]
    i = years.index(lf) if lf in years else len(years) - 1
    lf = years[i]

    cur_year = _year_of(rec.get("as_of"))
    if cur_year and lf < cur_year:
        return f"{sym}: latest_fy {lf} < current {cur_year} — keep"

    def at(arr, idx):
        return _num(arr[idx]) if 0 <= idx < len(arr) else None

    rev_l, ni_l, rev_p, ni_p = at(rev, i), at(ni, i), at(rev, i - 1), at(ni, i - 1)
    if rev_l is None or ni_l is None:
        return f"{sym}: latest-year revenue/ni missing — skip"

    # series (absolute AED, verified)
    rec["series"] = {"years": years, "revenue": [_num(x) for x in rev][:len(years)],
                     "net_income": [_num(x) for x in ni][:len(years)],
                     "operating_cash_flow": [_num(x) for x in ocf][:len(years)],
                     "source": "workflow-research"}
    # headline reported -> latest_fy (now consistently absolute AED)
    rep["revenue"], rep["net_income"] = rev_l, ni_l
    if rev_p is not None:
        rep["revenue_prior"] = rev_p
    if ni_p is not None:
        rep["net_income_prior"] = ni_p
    rep["net_margin"] = round(ni_l / rev_l, 4) if rev_l else None
    if rev_p and ni_p is not None:
        rep["net_margin_prior"] = round(ni_p / rev_p, 4)
    sh, eq, eps, dps = (_num(data.get("shares_outstanding")), _num(data.get("total_equity")),
                        _num(data.get("eps")), _num(data.get("dividend_per_share")))
    if sh and sh > 0:
        rep["shares_outstanding"] = sh
    if eq and eq > 0:
        rep["total_equity"] = eq
    if eps is not None:
        rep["eps"] = eps
    if dps is not None:
        rep["dividend_per_share"] = dps
        if eps and eps > 0:
            rep["payout_ratio"] = round(min(2.0, max(0.0, dps / eps)), 3)

    rec["as_of"] = f"FY{lf}"
    rec["source"] = f"FY{lf} results (workflow-verified)"
    srcs = data.get("sources") or []
    if srcs:
        rec["source_url"] = srcs[0]
    rec["extractor"] = "workflow-research-fy2025"
    rec["confidence"] = data.get("confidence", "medium")
    fp.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return f"{sym}: -> FY{lf} (rev {rev_l/1e9:.2f}bn, ni {ni_l/1e9:.2f}bn, eps {eps})"


def main():
    if len(sys.argv) < 2:
        print("usage: merge_fy2025.py <workflow_transcript_dir>"); sys.exit(1)
    best = extract(Path(sys.argv[1]))
    print(f"[fy2025] extracted {len(best)} symbols")
    rolled = 0
    for sym, data in sorted(best.items()):
        msg = merge_one(sym, data)
        if "-> FY" in msg:
            rolled += 1
        print("  " + msg)
    print(f"[fy2025] rolled {rolled}/{len(best)} to latest fiscal year")


if __name__ == "__main__":
    main()
