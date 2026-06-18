"""
World Bank commodity ("Pink Sheet" / CMO) adapter.

The blueprint uses World Bank commodity updates as the macro/commodity factor layer
(energy, metals, food, fertilizers, raw materials). The canonical source is the monthly
"Pink Sheet" workbook (xlsx). To keep the brain dependency-free (Khalid's light, free
ethos — no pandas/openpyxl required to run), this adapter:

  - reads a CSV snapshot if WB_PINKSHEET_CSV_URL is configured (the grounding research
    confirms the exact monthly URL), OR
  - reads a locally cached snapshot at research/commodities_snapshot.csv, OR
  - falls back to the deterministic demo snapshot (clearly tagged demo).

Columns expected in the CSV: series,label,value,unit  (one row per commodity).
"""
from __future__ import annotations

import csv
import io
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .base import CommodityPoint, Provenance, CommodityAdapter, SOURCE_OFFICIAL, DQ_EOD
from .mock import MockProvider

UTC = timezone.utc


def _iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class WorldBankProvider(CommodityAdapter):
    name = "worldbank"

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._fallback = MockProvider()
        self.csv_url = os.environ.get("WB_PINKSHEET_CSV_URL", "").strip()
        self.local = Path(__file__).resolve().parent.parent.parent / "research" / "commodities_snapshot.csv"

    def _from_rows(self, rows: list[dict]) -> list[CommodityPoint]:
        out: list[CommodityPoint] = []
        prov = Provenance(SOURCE_OFFICIAL, "World Bank (Pink Sheet)", DQ_EOD, _iso())
        for row in rows:
            try:
                out.append(CommodityPoint(
                    series=row["series"].strip(),
                    label=row.get("label", row["series"]).strip(),
                    value=float(row["value"]),
                    change_pct=float(row.get("change_pct", 0) or 0),
                    unit=row.get("unit", "").strip(),
                    as_of=row.get("as_of", _iso()),
                    prov=prov,
                ))
            except Exception:
                continue
        return out

    def snapshot(self) -> list[CommodityPoint]:
        # 1) remote CSV if configured
        if self.csv_url:
            try:
                req = urllib.request.Request(self.csv_url, headers={"User-Agent": "uae-stocks-intel/1.0"})
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    text = r.read().decode("utf-8", "replace")
                rows = list(csv.DictReader(io.StringIO(text)))
                pts = self._from_rows(rows)
                if pts:
                    return pts
            except Exception as e:  # noqa: BLE001
                print(f"[worldbank] remote CSV failed ({e}); trying local/demo")
        # 2) local cached snapshot
        if self.local.exists():
            try:
                rows = list(csv.DictReader(self.local.open()))
                pts = self._from_rows(rows)
                if pts:
                    return pts
            except Exception as e:  # noqa: BLE001
                print(f"[worldbank] local CSV failed ({e}); using demo")
        # 3) honest demo fallback
        return self._fallback.snapshot()
