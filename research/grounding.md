# UAE Stocks App — Architecture Grounding

Consolidated from 6 research probes run live on 2026-06-18. Status tags: **[VERIFIED]** = live curl/network capture; **[DOC]** = documented but not live-confirmed; **[ANALYTICAL]** = economic reasoning, not measured; **[FLAG]** = uncertain / needs human check before shipping.

---

## 1. Scope & Master Variables

The app displays AI-assisted *analysis/explainability* (not personalized buy/sell calls) over ADX + DFM + global-context data.

Two cross-sector master variables anchor every model:

1. **Fed/UAE policy rate (one driver).** AED is hard-pegged to USD at **3.6725** since 1997, so CBUAE shadows the Fed ~1:1. "US rates" ≈ "UAE rates" for equity modeling. **[VERIFIED]** peg / **[ANALYTICAL]** transmission.
2. **Oil price.** Drives UAE sovereign fiscal capacity → government project spend → bank liquidity/deposits → expat population → market sentiment. Even non-energy sectors carry an indirect "oil beta" via the fiscal/liquidity channel (stronger for Abu Dhabi/ADX names than Dubai/DFM). **[ANALYTICAL]**

USD/DXY is a secondary signal (EM risk-appetite + commodity inverse), muted by the peg.

---

## 2. Exchange Data Surfaces

### 2.1 ADX (Abu Dhabi Securities Exchange) — MIC `XADS`, tz Asia/Dubai

- Site is Next.js + Sitecore SPA behind **Cloudflare** (server-side curl → HTTP 403). **[VERIFIED]**
- Private JSON backend at `https://apigateway.adx.ae`. Envelope: `{response, resultCode:"S"|"F", resultMessage, errorMessages[]}`. Requires an **Authorization: Bearer** token the web app self-mints via `www.adx.ae/api/bpm/get-cookie?getAllCookie=true`; unauthenticated → HTTP 401 `{"errorMessages":["Unauthorized"]}`. **[VERIFIED]**
- Quote namespace is literally `marketwatch-delayed` = **15-minute delayed**. Real-time needs a logged-in ADX account or licensed feed. **[VERIFIED]**
- Live snapshot 18 Jun 2026: ADX General Index **FADGI = 10,037.24 (+0.411%)**; blue-chip index **FADX15** (FTSE ADX 15); 128 *listed securities* (all instruments) but only ~88 ordinary-equity tickers on the board. **[VERIFIED]**

Key ADX endpoints (all GET, all under `https://apigateway.adx.ae`):
| Purpose | Path |
|---|---|
| Full delayed equity board | `/adx/marketwatch-delayed/1.1/securityBoard/marketwatch` |
| Scrolling ticker | `/adx/marketwatch-delayed/1.1/scrollingTicker` |
| Top 5 by value | `/adx/marketwatch-delayed/1.1/topFiveValueCompany` |
| Big block trades | `/adx/marketwatch-delayed/1.1/bigBlockTrades` |
| Trading status | `/adx/marketwatch/1.1/trading-status` |
| Index intraday chart | `/adx/marketwatch/1.1/indexChartDay/FADGI` (segment = index code; FADX15 likely valid) |
| Listed-companies universe | `/adx/lookups/1.1/data/listed-companies` |
| Sector list | `/adx/lookups/1.1/data/sector` |
| Symbol→sector map | `/adx/lookups/1.1/data/symbol-sector` |
| Disclosures/news | `/adx/tradings/1.1/news/category` |
| Disclosure PDF | `/adx/cdn/1.0/content/download/{numericId}` |

Company profile (HTML/SPA): `www.adx.ae/en/main-market/company-profile/overview?symbols=SYMBOL` (param is `symbols=` plural; bare `?symbol=` does NOT trigger the API). All-equities DOM board renderable at `www.adx.ae/all-equities`. **[VERIFIED]**

### 2.2 DFM (Dubai Financial Market)

- Live quotes + DFMGI index over two socket.io v1 gateways: `dfeed.dfm.ae` (15-min delayed) and `rfeed.dfm.ae` (real-time). **[DOC]** (config-derived)
- JSON snapshot (delayed) via POST of symbol IDs: `https://marketwatch.dfm.ae/dapi/fetch` — internal session-cookie AJAX, not stable. **[DOC/FLAG]**
- Foreign-ownership DB (Permitted / Actual / Available per security, since Feb 2019): `www.dfm.ae/the-exchange/statistics-reports/foreign-ownership`. **[DOC]**
- Tiers: full Market Depth (L2) / standard L1 / **free 15-min-delayed post-trade**. Real-time self-service at `esrv.dfm.ae`. **[DOC]**
- Alias resolution: `ARMX`→Aramex, `MASQ`→Mashreq. GFH is dual-listed. **[DOC]**

### 2.3 Exchange assignment guardrail **[VERIFIED]**

These big names are **DFM, NOT ADX** — do not mis-file: Emaar Properties, Emaar Development, DEWA, Emirates NBD, Dubai Islamic Bank, du (EITC), Salik, Parkin, Empower, Mashreq, Amlak, Talabat, Tecom, DTC, Air Arabia, Aramex.
**Americana (AMR)** IS on ADX (dual-listed ADX + Saudi Tadawul 6015), not DFM.
**DP World** trades on **Nasdaq Dubai**, not ADX/DFM main board.

---

## 3. Global Context Data (free, no-key)

### 3.1 World Bank "Pink Sheet" / CMO **[VERIFIED 2026-06-18]**
- Monthly xlsx (HTTP 200, 588 KB): `https://thedocs.worldbank.org/en/doc/{DOCID}/related/CMO-Historical-Data-Monthly.xlsx`. Sheets: *Monthly Prices* (~70 series), *Monthly Indices* (2010=100 aggregates), *Index Weights*, *Description*. Monthly from 1960.
- Annual xlsx (3.18 MB) and monthly PDF (`CMO-Pink-Sheet-<Month>-<Year>.pdf`) same folder.
- **The `{DOCID}` folder rolls ~quarterly** (current: `74e8be41ceb20fa0da750cda2f6b9e4e-0050012026`). DO NOT hardcode — scrape `worldbank.org/en/research/commodity-markets` for the current `related/...Monthly.xlsx` href; trailing filename is stable. Next update was 2 Jul 2026. **[FLAG: rolling id]**
- Pink Sheet prices are **file-based, NOT in the Indicators API** (PINKEDATA probe → error id 120). Use Indicators API v2 (`api.worldbank.org/v2/...?format=json`) only for macro series. **[VERIFIED]**

Series→sector keys: CRUDE_BRENT/WTI/DUBAI → Energy/Banks/RealEstate(indirect)/Aviation(cost); NGAS_* → Petrochem+Fertilizer feedstock, Utilities fuel, ADNOC Gas; UREA/DAP/Potash/Phosphate → Fertiglobe; ALUMINUM/IRON_ORE/steel → RealEstate construction + Food packaging; WHEAT/MAIZE/RICE/SOYBEAN_OIL/PALM_OIL/SUGAR → Food/Agri COGS + fertilizer demand. **[ANALYTICAL]** (confirm exact STEEL/REBAR & DAIRY column headers per vintage — **[FLAG]**)

### 3.2 GDELT DOC 2.0 **[VERIFIED 2026-06-18]**
- Base: `https://api.gdeltproject.org/api/v2/doc/doc`. `format=json`. Modes: `artlist` (fields: url, url_mobile, title, seendate, socialimage, domain, language, sourcecountry), `tonechart`, `timelinevol`, `timelinetone`. maxrecords default 75 / max 250. Lookback ~3 months only (current-news sentiment, not history backfill).
- **Rate limit: ~1 request / 5 seconds / IP → HTTP 429** plaintext. Space ≥5s, exponential backoff. **[VERIFIED]**
- Theme-filtered queries drive per-sector news factors: `theme:ECON_INTEREST_RATE` (rate factor), `theme:ECON_OILPRICE`, `theme:TOURISM`, `theme:AGRICULTURE`, trade/maritime, `NATURAL_DISASTER` (insurance). **[ANALYTICAL]**
- GEO 2.0 GeoJSON (`/api/v2/geo/geo`) returned 404 from the probe IP while `/doc/doc` worked — treat as **[DOC, not curl-confirmed; FLAG]**.

---

## 4. Compliance (onshore SCA + ADX/DFM)

### 4.1 SCA Finfluencer regime — Resolution No. 10/R.M of 2025 (eff. 20 May 2025) **[VERIFIED scope, DOC verbatim]**
- A "financial recommendation" is read **broadly**: buy/sell calls, price targets, "will go up" statements, even neutral statements implying future gains on a named product, to people in the UAE (UAE or foreign products).
- Register requires: SCA-accredited analyst OR CFA OR qualifying "market-trader influencer" (~1,000+ followers / ~6 mo experience / media-quoted). Fee AED 5,000; UAE citizens fee-exempt 3 yrs from 20 May 2025. Decision in 5 working days. Unregistered in-scope activity = fines + blacklisting.
- **Safe posture for the app (key strategic finding):** frame AI output as research-support / factual / educational context — **NOT personalized buy/sell/hold**. Specifically: (i) no named buy/sell/hold calls, price targets, or "will go up" on specific tickers; (ii) descriptive/analytical not directive; (iii) no personalization to user circumstances; (iv) persistent disclaimers ("past performance is not indicative…"; show publish date/time; flag high-risk; disclose conflicts); (v) if it ever crosses into recommendations for UAE users, route through an SCA-registered finfluencer/licensed entity.
- **[FLAG]** Legal analyses do NOT confirm an explicit statutory carve-out for "educational"/"news"/"general info" content — the regime is "intentionally comprehensive." This is risk-mitigation, not a guaranteed exemption. Pull the verbatim Arabic/English PDF from `sca.gov.ae/en/regulations/regulations-listing.aspx` and get UAE securities counsel sign-off.
- Register (`Simple.charts_ae` confirmed = Sulaiman Abdalla Sulaiman Alnaqbi, 17-Jul-2025): use the **beta** host `beta.sca.gov.ae/en/open-data/financial-recommendations-provider.aspx` (www host rendered empty). ~85 entries by Sep-2025. **[VERIFIED]**

### 4.2 Market-data licensing **[DOC / standard practice]**
- Cheapest compliant path = **15-min delayed** data via an authorized vendor under a **redistribution + display** license, with **non-professional** user attestation.
- Four fee axes: real-time vs delayed; display vs non-display; professional vs non-professional; redistribution (per-subscriber, scales with users).
- Using `apigateway.adx.ae` / `marketwatch.dfm.ae` programmatically is effectively **scraping** the exchanges' private backends — check ADX Terms of Use + DFM terms before redistributing. **[FLAG]** Exact ADX Terms text was Cloudflare-blocked; verify reuse clause in a browser before shipping.
- Licensed vendors: ICE Global Network / ICE Consolidated Feed, LSEG/Refinitiv, plus aggregators (Twelve Data XADS, EODHD, Intrinio, FactSet). Exact fee schedules are negotiated, not published.

---

## 5. AI Layer (verified vs `claude` 2.1.177)

- **Free default lane:** `claude` print mode with a native **JSON-Schema flag** that constrains output to a supplied schema (no prompt-only structured output). Append analyst persona to system prompt, model `sonnet`, tools disabled, session persistence off, spend capped. **[VERIFIED]**
- Envelope fields: `is_error`, `api_error_status`, `result`, `total_cost_usd`, `usage`. The real answer is `result` — a **serialized string**: parse stdout once, then parse `result` again. **[VERIFIED]**
- **Critical trap:** exit code stays **0 even on auth failure** → branch on `is_error`, never the exit code. **[VERIFIED]**
- Auth: Max OAuth login or `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` (launchd plist for unattended). **NEVER set `ANTHROPIC_API_KEY`** on this lane (switches to paid metered billing). `total_cost_usd` reports 0 on the Max sub. **[VERIFIED]**
- **Paid fallback:** OpenAI Structured Outputs, opt-in via `AI_PROVIDER=openai`, reads `OPENAI_API_KEY` at call time. Strict mode is stricter: `additionalProperties:false` on every object, every key in `required`, optionals as `["type","null"]` unions. **Author one strict schema to OpenAI rules → serves both providers + stub.** **[VERIFIED/DOC]**
- The auth failure in the research sandbox is a sandbox artifact (base-URL override, keychain skipped) — confirm in Khalid's shell with `claude auth status`. **[FLAG]**

---

## 6. Recommended Build Posture

- **Data:** ship on **15-min delayed** ADX + DFM via authorized vendor (display + redistribution + non-pro attestation). For prototyping, drive a headless/real Chrome against the SPA DOM or the gateway, but treat that as scraping and resolve licensing before launch.
- **Universe/sector tags:** ADX `lookups/symbol-sector`; DFM portal. Cache the lookup tables; refresh weekly.
- **Global context:** WB Pink Sheet monthly xlsx (scrape landing for current DOCID) + GDELT DOC 2.0 (≥5s spacing, 429 backoff).
- **AI:** free `claude` schema lane default; OpenAI fallback behind `AI_PROVIDER`; one strict schema module; cache by hash(task + schema_version + input) in the GitHub-repo DB so re-runs are free; re-validate every returned object before the ledger; for Arabic filings state output language in the system prompt.
- **Compliance:** descriptive-not-directive framing, persistent disclaimers, no named calls/targets — and get counsel sign-off on Resolution 10/R.M before public launch.