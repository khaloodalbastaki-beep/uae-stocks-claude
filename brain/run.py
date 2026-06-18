"""
Entrypoint for the UAE Stocks Intelligence brain.

Usage:
    python -m brain.run                 # full demo build -> ./data
    python -m brain.run --live          # live free feeds + any existing approved quote file
    python -m brain.run --limit 6       # quick subset (fast dev loop)
    python -m brain.run --out /path     # custom output dir

Env:
    UAE_PROVIDER=mock|live              # exchange data lane (default mock)
    UAE_AI_PROVIDER=stub|claude|openai  # AI narration lane (default stub, free+offline)
    UAE_AI_MODEL=...                    # optional model override for claude/openai
    WB_PINKSHEET_CSV_URL=...            # optional live World Bank commodity CSV
"""
from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

from .pipeline import Pipeline


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the UAE Stocks Intelligence data set.")
    ap.add_argument("--live", action="store_true", help="use live free feeds plus any existing approved delayed quote file")
    ap.add_argument("--limit", type=int, default=None, help="process only N securities")
    ap.add_argument("--out", type=str, default=None, help="output data dir")
    args = ap.parse_args()

    if args.live:
        os.environ.setdefault("UAE_PROVIDER", "live")

    out = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "data"
    t0 = time.time()
    pipe = Pipeline(out, live=args.live, limit=args.limit)
    meta = pipe.run()
    dt = time.time() - t0
    print(f"[brain] built {meta['counts']['securities']} securities + "
          f"{meta['counts']['events']} events -> {out} in {dt:.1f}s "
          f"(provider={meta['provider']}, ai={meta['ai_provider']})")


if __name__ == "__main__":
    main()
