"""Reads data/news/<SYMBOL>.json (live GDELT media coverage written by brain.news) for the
News & Disclosures tab. Returns [] when there's no cached news (caller falls back to the
mock disclosure flow, which stays clearly badged)."""
from __future__ import annotations

import json
from pathlib import Path


class NewsStore:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir) / "news"

    def items(self, symbol: str) -> list[dict]:
        f = self.dir / f"{symbol}.json"
        if not f.exists():
            return []
        try:
            rec = json.loads(f.read_text())
            out = []
            for it in rec.get("items", []):
                out.append({**it, "retrieved_at": rec.get("retrieved_at"),
                            "feed_source": rec.get("source", "GDELT (live media)")})
            return out
        except Exception:
            return []
