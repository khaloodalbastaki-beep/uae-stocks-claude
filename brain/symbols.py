"""Emit the registry symbol list as JSON for the Node scraper (keeps registry.py the
single source of truth; the scraper reads data/symbols.json rather than hardcoding names).

    python3 -m brain.symbols > data/symbols.json
"""
import json
import sys

from .registry import load_universe

def main() -> None:
    rows = [{
        "symbol": s.symbol,
        "exchange": s.exchange,
        "name_en": s.name_en,
        "aliases": s.aliases,
    } for s in load_universe()]
    json.dump(rows, sys.stdout, ensure_ascii=False)

if __name__ == "__main__":
    main()
