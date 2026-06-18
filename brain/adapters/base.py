"""
Adapter interfaces + the provenance model.

Two blueprint principles drive this file:
  1. "Do not hardcode a single data provider in a way that prevents future licensing
     changes." -> everything is an interface; the pipeline picks an implementation.
  2. "Every derived insight must link back to evidence. The UI must always preserve
     source provenance and timestamps." -> every payload object carries Provenance.

Source-type taxonomy (the compliance spine the blueprint demands — "separate official
fact from media from opinion from AI interpretation"):
    official  - exchange / issuer filing (highest trust)
    media     - news (WAM, press)
    opinion   - analyst consensus / authorised community view
    ai        - app-generated summary/analysis (must be labelled)
    mock      - demo data, NOT real (shown with a loud DEMO badge)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict

SOURCE_OFFICIAL = "official"
SOURCE_MEDIA = "media"
SOURCE_OPINION = "opinion"
SOURCE_AI = "ai"
SOURCE_MOCK = "mock"

# data_quality
DQ_REALTIME = "realtime"
DQ_DELAYED = "delayed"
DQ_EOD = "eod"
DQ_DEMO = "demo"


@dataclass
class Provenance:
    source_type: str            # one of SOURCE_*
    source_name: str            # "ADX", "DFM", "WAM", "World Bank", "App AI (claude)"
    data_quality: str           # one of DQ_*
    retrieved_at: str           # ISO8601
    url: str | None = None
    lang: str | None = None     # 'ar' | 'en' for documents

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Quote:
    symbol: str
    price: float
    change: float               # absolute
    change_pct: float           # decimal, e.g. 0.013
    volume: int
    market_cap: float | None
    high_52w: float | None = None
    low_52w: float | None = None
    spark: list[float] = field(default_factory=list)   # ~30d closes for sparkline
    prov: Provenance | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["prov"] = self.prov.to_dict() if self.prov else None
        return d


@dataclass
class Disclosure:
    id: str
    symbol: str
    event_type: str             # results|board_meeting|agm_invitation|agm_resolution|dividend|acquisition|capital_raise|governance|subsidiary|other
    title_src: str              # original title (may be Arabic)
    title_en: str               # English (translation if needed)
    title_lang: str             # 'ar' | 'en'
    published_at: str
    body_excerpt: str = ""
    url: str | None = None
    # AI-derived (filled by ai layer; never invented numbers)
    summary_en: str = ""
    summary_ar: str = ""
    why_it_matters: str = ""
    materiality: int = 0        # 0..100
    sentiment: str = "neutral"  # positive|neutral|cautious|negative
    linked_entities: list[str] = field(default_factory=list)
    prov: Provenance | None = None
    translation_app_generated: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["prov"] = self.prov.to_dict() if self.prov else None
        return d


@dataclass
class Meeting:
    symbol: str
    kind: str                   # board|agm|egm
    date: str
    status: str                 # upcoming|held
    agenda: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)   # dividend|capital_increase|buyback|acquisition|board_election
    resolutions: list[str] = field(default_factory=list)
    outcome_summary: str = ""
    prov: Provenance | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["prov"] = self.prov.to_dict() if self.prov else None
        return d


@dataclass
class DividendEvent:
    symbol: str
    amount: float               # AED per share
    currency: str = "AED"
    agm_date: str | None = None
    entitlement_date: str | None = None
    ex_date: str | None = None
    payment_date: str | None = None
    frequency: str = "annual"
    fiscal_year: str | None = None
    prov: Provenance | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["prov"] = self.prov.to_dict() if self.prov else None
        return d


@dataclass
class OwnershipSnapshot:
    symbol: str
    top_holders: list[dict] = field(default_factory=list)   # {name, pct}
    foreign_permitted: float | None = None
    foreign_actual: float | None = None
    foreign_available: float | None = None
    free_float: float | None = None
    prov: Provenance | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["prov"] = self.prov.to_dict() if self.prov else None
        return d


@dataclass
class CommodityPoint:
    series: str                 # CRUDE_BRENT, UREA_EE_BULK, ...
    label: str
    value: float
    change_pct: float
    unit: str
    as_of: str
    prov: Provenance | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["prov"] = self.prov.to_dict() if self.prov else None
        return d


@dataclass
class GlobalEvent:
    title: str
    theme: str
    published_at: str
    domain: str
    url: str | None = None
    tone: float = 0.0           # GDELT tone (-100..100)
    prov: Provenance | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["prov"] = self.prov.to_dict() if self.prov else None
        return d


# ---------------------------------------------------------------------------
# Interfaces — a provider implements whichever it can; pipeline composes them.
# ---------------------------------------------------------------------------
class QuoteAdapter(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> Quote | None: ...


class DisclosureAdapter(ABC):
    @abstractmethod
    def list_disclosures(self, symbol: str, limit: int = 20) -> list[Disclosure]: ...


class CorporateActionsAdapter(ABC):
    @abstractmethod
    def meetings(self, symbol: str) -> list[Meeting]: ...
    @abstractmethod
    def dividends(self, symbol: str) -> list[DividendEvent]: ...


class FundamentalsAdapter(ABC):
    @abstractmethod
    def get_fundamentals(self, symbol: str): ...     # -> scoring.Fundamentals


class OwnershipAdapter(ABC):
    @abstractmethod
    def get_ownership(self, symbol: str) -> OwnershipSnapshot | None: ...


class CommodityAdapter(ABC):
    @abstractmethod
    def snapshot(self) -> list[CommodityPoint]: ...


class EventsAdapter(ABC):
    @abstractmethod
    def global_events(self, query: str, limit: int = 8) -> list[GlobalEvent]: ...
