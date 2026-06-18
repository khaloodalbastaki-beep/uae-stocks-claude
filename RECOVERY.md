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
- **Fundamentals:** REAL reported FY2024 for **52/54** names (only ADNH + Q modeled). Stored
  in `data/fundamentals/<SYM>.json` (reported figures + source URL + as_of). The brain derives
  Growth/Stability/Dividend deterministically from them (LLM only transcribes). UI shows a
  "real fundamentals" badge + source per stock.
- **News:** LIVE media per company from GDELT (`brain/news.py` → `data/news/<SYM>.json`),
  relevance-filtered (UAE/Gulf/finance whitelist) so it's on-topic. News & Disclosures tab
  renders it with a "live" badge; demo fallback if a name isn't fetched yet.
- **AI Analysis:** stance + confidence + scores are DETERMINISTIC; the prose (reasons/risks/
  what-would-change) is written by the **nemotron** fleet agent → `data/ai/<SYM>.json`, shown
  as "narrated by nemotron".
- **UX:** stock page has a ← Back button; navigation closes the search dropdown + scrolls top.

## The agent fleet (manager = Claude Code) — `agents/FLEET.md`
Free local Nous CLI agents (`<agent> chat -Q -q "<prompt>"`), wrapped by
`brain/ai/provider.py:CliAgentProvider` (`UAE_AI_PROVIDER=cli:<agent>`):
- **nemotron** (nvidia/nemotron-3-ultra:free) — **Analyst**: AI-tab prose. `python3 -m brain.analyst --stale N`.
- **freeagent** (stepfun/step-3.7-flash:free) — news-editor / backup analyst (`ANALYST_AGENT=freeagent`).
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
1. (Optional) a Gemini key with free quota → flip Mizan to `hybrid` for grounded+strong extraction.
2. ADNH + Q fundamentals (sparse public sources) — fill when available.
3. SCA/legal sign-off before marketing as more than a demo.
4. Phase-2: alerts → Telegram/Hermes; official exchange-filing feed (vs media news); semantic search.
