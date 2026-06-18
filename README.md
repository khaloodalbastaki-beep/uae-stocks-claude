# UAE Stocks Intelligence

Investor-intelligence app for **ADX & DFM** listed equities — official disclosures,
dividend logic, board/AGM governance, a global-factor exposure map, and an **explainable**
AI analysis layer. English + Arabic, mobile-first, dark/light.

Built on **Khalid's ecosystem**, not a heavyweight enterprise stack:

```
  Python brain (Mac mini, launchd)  ─emit─▶  plain JSON  ─▶  static PWA on GitHub Pages
  deterministic scoring + adapters            (GitHub-as-DB,            (free hosting,
  + AI narration (free claude lane)            agentec pattern)          add-to-home-screen)
```

This is the same pattern as the finance, agentec and hypertrophy apps: **deterministic
Python owns every number; the LLM only narrates; the frontend is a free static PWA that
reads JSON.** No database server, no Docker, no paid hosting, no mandatory API key — it
runs end-to-end for **AED 0**.

> Why not the Codex/Next.js+Postgres+Docker+OpenAI build the blueprint prompt asks for?
> That stack needs paid hosting, a managed DB, and an OpenAI key just to boot, and it
> hardcodes a provider the blueprint itself warns against. This build delivers the same
> product vision on rails Khalid already runs and can ship tonight. See `ARCHITECTURE.md`.

---

## Quick start

```bash
cd ~/Projects/uae-stocks
python3 -m brain.run            # build the demo dataset -> ./data  (offline, free)
bash tools/build.sh             # build data + icons + web/data + dist/
# preview: serve web/ as a static dir, e.g.
python3 -m http.server 8812 --directory web   # open http://127.0.0.1:8812
```

No pip install required — the brain is **stdlib-only** by design.

### Modes

| Concern | Env var | Default | Options |
|---|---|---|---|
| Exchange data | `UAE_PROVIDER` | `mock` | `mock` \| `live` |
| AI narration | `UAE_AI_PROVIDER` | `stub` | `stub` \| `claude` \| `openai` |
| AI model | `UAE_AI_MODEL` | — | model id for claude/openai |
| Commodity feed | `WB_PINKSHEET_CSV_URL` | — | live World Bank CSV |

- **`mock` + `stub`** → fully offline, deterministic, AED 0. Realistic placeholder figures
  for the *real* ADX/DFM universe (tickers, sectors, exposure map are real; quotes are
  demo and loudly badged).
- **`live`** → turns on the free no-key feeds (GDELT events, World Bank commodities) and
  may read an already-produced `data/live_quotes.json` file for delayed ADX/DFM quotes.
  It does **not** scrape exchanges by itself.
- **`claude`** → narration via your local `claude` CLI (Claude Max), no API key, free.
- **`openai`** → optional paid lane; only active if `OPENAI_API_KEY` is set.

```bash
UAE_AI_PROVIDER=claude python3 -m brain.run      # narrate with the free claude lane
python3 -m brain.run --live                       # live macro/event feeds + any existing approved quote file
python3 -m brain.run --limit 6                     # fast dev subset
```

---

## What's in the box

```
brain/                      # the Mac-mini "brain" (deterministic, launchd)
  registry.py               # canonical securities universe (real ADX/DFM tickers + exposure map)
  factors.py                # global driver definitions (oil, rates, urea, freight, …)
  scoring.py                # deterministic Growth/Stability/Dividend (0-100) + full breakdown
  adapters/
    base.py                 # provenance model + adapter interfaces (no hardcoded provider)
    mock.py                 # realistic, deterministic demo data (tagged demo)
    exchanges.py            # ADX/DFM live adapters (documented, license-gated stubs)
    livescrape.py           # optional delayed quote file reader, falls back per symbol
    gdelt.py                # LIVE free global-events adapter (stdlib)
    worldbank.py            # commodity Pink-Sheet adapter (CSV/cache/demo)
  ai/
    provider.py             # provider-agnostic AI: stub | claude CLI | openai
    schemas.py              # JSON schemas for extraction + analysis
    narrate.py              # disclosure enrichment + AI Analyze (deterministic stance, LLM prose)
  pipeline.py               # ingest -> score -> narrate -> emit JSON
  run.py                    # CLI entrypoint
web/                        # static PWA (no build step, vanilla JS)
  index.html, css/, js/     # SPA: home + 8-tab stock page + watchlist/alerts/screeners
  manifest.json, sw.js      # installable, offline-first
data/                       # emitted JSON (the GitHub-as-DB payload)
  launch_readiness.json     # deterministic launch blockers / safety checks for Admin
tools/                      # build.sh, deploy.sh, make_icons.py
launchd/                    # com.bastaki.uae-stocks-ingest.plist (recurring brain)
research/                   # grounding doc + enriched universe (from the research run)
```

## Routes (SPA)
`#/` home · `#/markets/{adx,dfm,all}` · `#/stock/{SYMBOL}` · `#/watchlist` · `#/alerts`
· `#/screeners` · `#/global-factors` · `#/ipos` · `#/admin` (ingestion health)
`#/admin` also renders the deterministic launch-readiness ledger: live-feed gate status,
data-rights blocker, SCA sign-off blocker, holdings isolation, public scratch-file guard,
and the LLM boundary.

## Stock page tabs
Overview · News & Disclosures · Meetings · Financials · Dividends · Ownership ·
Global Factors · AI Analysis.

---

## Design principles (and where they live in code)

- **Numbers from code, never the LLM.** `brain/scoring.py` computes the three house scores
  deterministically with a transparent sub-factor breakdown; `ai/narrate.py` is explicitly
  forbidden from producing scores or the headline call — it only writes prose.
- **Official fact > media > opinion > AI.** Every payload object carries `Provenance`
  (`brain/adapters/base.py`); the UI renders source badges + timestamps and keeps the
  four tiers visually separate.
- **Arabic is a product principle.** Source language is preserved; translation is badged
  app-generated; Arabic is marked the official text.
- **Honest-degraded > fake-good.** Live adapters fall back to demo and tag the data; demo
  figures are never presented as real quotes.
- **Free by default; paid path parked.** Default lanes are free/owned; OpenAI and licensed
  feeds are wired but off until explicitly enabled.

## Data rights (the #1 risk, handled up front)
ADX Terms forbid copying/derivative works without authorisation; DFM marks Arabic as the
official text and English as informational. So the launch posture (the blueprint's own
recommendation) is: **public delayed quotes + official disclosures first, licensed
real-time later.** `tools/refresh.sh` is the only unattended headless exchange-scrape +
public deploy path, and it exits unless `UAE_ALLOW_LIVE_EXCHANGE=1` is set after Khalid's
explicit approval/licensing decision. The lower-level endpoint adapters also stay gated
behind `UAE_PROVIDER=live` + a per-source `verified` flag + `ENABLE_<EX>_LIVE=1`.

## Compliance
Positioned as **research support / explainability, not personalised investment advice**
(UAE SCA framework). Disclaimers ship in the footer and the AI tab; the AI stance is
deterministic and explained, not a black-box recommendation.

## Roadmap
- **Phase 1 (this build):** ADX/DFM universe, delayed/demo prices, disclosures, board/AGM
  timelines, dividend dates + sustainability, bilingual summaries, scores, exposure map,
  watchlist/alerts, explainable AI. ✔
- **Phase 2:** licensed real-time feed, two-way GitHub data sync, Telegram/Hermes alert
  push, issuer-IR ingestion, consensus, foreign-ownership change tracking, semantic search
  (embeddings).
- **Phase 3:** Nasdaq Dubai / REITs / ETFs / sukuk, portfolio logic, event-impact scoring.
