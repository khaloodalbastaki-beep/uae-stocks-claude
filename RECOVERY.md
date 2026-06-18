# UAE Stocks Intelligence — Claude instance — REVIVAL PROMPT

> Read this to re-enter the project cold. This is the **Claude live instance**, fully
> decoupled from Codex's `~/Projects/uae-stocks` (demo, gated). Local access only.

## What it is
A UAE public-markets intelligence PWA (ADX + DFM) built from
`~/Downloads/UAE Equities Intelligence App Blueprint.docx` as a head-to-head vs Codex, on
Khalid's free ecosystem (deterministic Python brain on the Mac mini → plain JSON →
GitHub-as-DB → static bilingual EN/AR PWA on GitHub Pages). Numbers from code; LLMs only
narrate; free by default.

## LIVE
- **App:** https://khaloodalbastaki-beep.github.io/uae-stocks-live/ (add-to-home-screen PWA)
- **Source repo:** GitHub `khaloodalbastaki-beep/uae-stocks-claude`; **Pages repo:** `uae-stocks-live`
- **Code root:** `~/Projects/uae-stocks-claude`

## Current state (2026-06-19)
- **Prices:** REAL ~15-min delayed ADX + DFM, + real FADGI/DFMGI indices. Source = headless-
  Chromium scraper (`scraper/scrape.mjs`, Playwright) reading the ADX all-equities board +
  DFM marketwatch search; keyed to the registry. Yahoo/ADX-API are blocked, so the browser
  scrape is the working free path. Tagged `delayed`; per-symbol demo fallback.
- **Fundamentals:** REAL reported FY2024 for **53/53** names (FULL coverage). Stored
  in `data/fundamentals/<SYM>.json` (reported figures + source URL + as_of). The brain derives
  Growth/Stability/Dividend deterministically from them (LLM only transcribes). UI shows a
  "real fundamentals" badge + source per stock. (Universe is 53: the defunct ticker `Q`/Q Holding
  was dropped 2026-06-19 — it rebranded to Modon Holding, already listed as `MODON`.)
- **News:** LIVE media per company from GDELT (`brain/news.py` → `data/news/<SYM>.json`),
  relevance-filtered (UAE/Gulf/finance whitelist) so it's on-topic. News & Disclosures tab
  renders it with a "live" badge; demo fallback if a name isn't fetched yet.
- **AI Analysis:** stance + confidence + scores are DETERMINISTIC; the prose (reasons/risks/
  what-would-change) is written by the **nemotron** fleet agent → `data/ai/<SYM>.json`, shown
  as "narrated by nemotron".
- **Financials (REAL):** 3–4y reported series (revenue / net income / operating cash flow) for
  all 53, in `data/fundamentals/<SYM>.json["series"]` (absolute AED, gathered + skeptically
  audited by a workflow). The Financials tab charts now render REAL value-labelled bars (no more
  "Demo data") — `brain.pipeline._financial_trends` uses the series, falls back to demo only if
  absent. NOTE: the seed `reported.revenue/net_income` are MIXED-UNIT (millions for some, absolute
  for others) — scoring is scale-invariant so unaffected, but level math (valuation) must use the
  `series` (absolute), never `reported`.
- **Fair value (REAL, deterministic):** `brain/valuation.py` computes a per-share intrinsic value
  for **52/53** (DDM + justified P/B-ROE + growth-tilted earnings multiple, blended by archetype;
  perpetual-g capped ≥3.5pt below the discount rate; one-off-earnings normalised for the multiple;
  outlier methods dropped; ≥2 methods required else None). Payload `valuation{fair_value, upside_pct,
  rating, confidence, methods, assumptions}`. UI: a **Fair value card** on the Financials tab
  (fair vs live price, upside, method breakdown, assumptions, "not advice") + a fair-value line on
  Overview. Valuation inputs (shares_outstanding/total_equity/eps) live in `reported`.
- **UX:** stock page has a ← Back button; navigation closes the search dropdown + scrolls top.

## The agent fleet (manager = Claude Code) — `agents/FLEET.md`
Free local Nous CLI agents (`<agent> chat -Q -q "<prompt>"`), wrapped by
`brain/ai/provider.py:CliAgentProvider` (`UAE_AI_PROVIDER=cli:<agent>`):
- **nemotron** (nvidia/nemotron-3-ultra:free) — **Analyst**: AI-tab prose. `python3 -m brain.analyst --stale N`.
  Note: nemotron needs ~210s on the narration prompt, so the analyst CLI timeout is **300s**
  (`ANALYST_TIMEOUT`, or `UAE_AI_CLI_TIMEOUT` for all CLI agents) — the old 90s default made the
  hourly run fail 0/N. If the primary times out / returns nothing it **auto-falls back to freeagent**
  (`ANALYST_BACKUP_AGENT`, flash ~13s) so the AI tab always gets prose; the JSON records the real narrator.
- **freeagent** (stepfun/step-3.7-flash:free) — news-editor / backup analyst (`ANALYST_AGENT=freeagent`; also the auto-fallback).
- **robin** — watcher/QA.
- **Mizan** (ميزان, `agents/mizan/`) — fundamentals extractor on **gpt-oss:120b-cloud** (Ollama
  Cloud, already signed in via `ollama signin`, no key). Default lane `web` (self-fetch IR
  page + Wikipedia → gpt-oss extracts); a `hybrid` gemini-grounded lane exists but needs a
  Gemini key with free quota (the one tried was 429 quota-blocked). `agents/mizan/RUNBOOK.md`.
- REMOVED 2026-06-19: ZenMux trio glm52/kimi27/step37 (403 paid-credits gate, against
  free-by-default). Backup: `~/.hermes/removed-zenmux-*.tar.gz`.

## Schedules (launchd, on the Mac mini)
- **`com.bastaki.uae-stocks-claude`** — every 15 min: `tools/refresh.sh` = scrape prices →
  `brain.run --live` (rebuilds reading fundamentals/news/ai caches) → deploy to `uae-stocks-live`.
- **`com.bastaki.mizan-refresh`** — hourly: `agents/mizan/refresh_cron.sh` = Mizan `--stale 4`
  (fundamentals) + `brain.news --stale 6` + `brain.analyst --stale 4`. All staleness-rotated
  (skip recently-touched, never repeat the freshest) to stay inside free rate limits.
- Logs: `data/ingest.log` (prices), `data/mizan.log` (hourly fleet).

## Run / rebuild / deploy
```bash
cd ~/Projects/uae-stocks-claude
python3 -m brain.run --live                         # rebuild data (reads all caches)
PAGES_REPO=khaloodalbastaki-beep/uae-stocks-live bash tools/refresh.sh --force   # scrape+build+deploy
python3 -m unittest discover -s tests               # scoring tests
python3 -m brain.news --symbols EMAAR               # refresh one name's news
python3 -m brain.analyst --symbols EMAAR            # re-narrate one name (nemotron)
python3 agents/mizan/mizan.py --symbols EMAAR       # re-extract one name's fundamentals (gpt-oss web lane)
```
Re-gather multi-year statements (Financials series + valuation inputs): run the
`uae-financials-gather` Workflow (gather→verify, one agent per stock; absolute-AED schema), then
`python3 tools/merge_statements.py <workflow_transcript_dir>` to enrich `data/fundamentals/`
(adds `series` + shares_outstanding/total_equity/eps; never overwrites verified fields). Then rebuild.
Preview: launch.json config `uae-stocks-claude` (port 8814, serves `web/`).

## Rules baked in (don't break)
- Numbers/scores/stance from deterministic code; agents only narrate/classify. Never let an
  LLM produce a price, score, or recommendation.
- Real-data-sacred: figures are tagged + sourced; demo is loudly badged; honest-degraded
  (keep-prior / found=false) over fabrication.
- Free-by-default: every lane is free (Nous agents, gpt-oss cloud via signin, GDELT,
  Wikipedia, World Bank). No paid keys.
- SCA posture: "research support, not advice"; disclaimers in footer + AI tab.
- Data-rights: the scraper reads public delayed boards; this is the demo/personal posture.
  SCA counsel sign-off + a licensed feed are the gates before any real public launch.

## Open / next
1. (Optional, NOT required) a Gemini free-quota key → Mizan `hybrid`. The keyless `web` lane
   (gpt-oss:120b-cloud via signed-in Ollama, no key) is the default and covers refresh, so the
   whole system runs with ZERO manual input. Hybrid is only a quality upgrade, not a dependency.
2. ~~ADNH + Q fundamentals~~ DONE 2026-06-19 — ADNH FY2024 added (grounded research); Q dropped
   (rebranded → Modon). Universe is full at 53/53 real fundamentals.
3. SCA/legal sign-off before marketing as more than a demo.
4. Phase-2: alerts → Telegram/Hermes; official exchange-filing feed (vs media news); semantic search.
