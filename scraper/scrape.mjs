/* UAE board scraper — real, ~15-min-delayed ADX + DFM quotes via headless Chromium.
 *
 * Reads ../data/symbols.json (the registry list, single source of truth) and produces
 * ../data/live_quotes.json keyed by REGISTRY symbol, so the Python brain just looks up by
 * its own symbol. Two read strategies:
 *   ADX  — the full board renders as a react-data-table (.rdt_TableRow); scrape all 127,
 *          match registry ADX symbols (and aliases, e.g. AMERICANA->AMR).
 *   DFM  — the default marketwatch shows only a partial watchlist, so we use its search
 *          autocomplete per registry DFM symbol: each suggestion is a `.ticker-item` with
 *          data-symbol + "SYM price (pct%)" text + an `increase`/`decrease` class (= sign).
 *
 * Khalid authorised "read from websites" for real data; this is free, no key, no account.
 * Quotes are tagged DELAYED (~15 min, per ADX's own banner) — never "real-time".
 */
import { chromium } from 'playwright';
import { writeFileSync, readFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const DATA = join(__dir, '..', 'data');
const OUT = join(DATA, 'live_quotes.json');
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

const num = (s) => {
  if (s == null) return null;
  const v = parseFloat(String(s).replace(/\s+/g, '').replace(/,/g, '').replace('%', ''));
  return Number.isFinite(v) ? v : null;
};

let registry = [];
try { registry = JSON.parse(readFileSync(join(DATA, 'symbols.json'), 'utf8')); }
catch { console.error('[scrape] no data/symbols.json — run `python3 -m brain.symbols > data/symbols.json` first'); }
const adxTargets = registry.filter((r) => r.exchange === 'ADX');
const dfmTargets = registry.filter((r) => r.exchange === 'DFM');

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US', viewport: { width: 1600, height: 1200 } });
const page = await ctx.newPage();

const quotes = {};
const indices = { adx: null, dfm: null };

// ---------------- ADX: full react-data-table board ----------------
try {
  await page.goto('https://www.adx.ae/all-equities', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForSelector('.rdt_TableRow', { timeout: 25000 });
  await page.waitForTimeout(3000);
  const { headers, rows, index } = await page.evaluate(() => {
    const headers = [...document.querySelectorAll('.rdt_TableCol')].map((e) => e.innerText.trim());
    const rows = [...document.querySelectorAll('.rdt_TableRow')].map((tr) =>
      [...tr.querySelectorAll('.rdt_TableCell')].map((c) => c.innerText.trim().replace(/\s+/g, ' ')));
    const hdr = [...document.querySelectorAll('*')].find((e) => {
      const t = (e.innerText || '').replace(/\s+/g, ' ').trim();
      return t.length < 70 && /FADGI/.test(t) && /\d,\d{3}\.\d/.test(t);
    });
    return { headers, rows, index: hdr ? hdr.innerText.replace(/\s+/g, ' ').trim() : null };
  });
  const col = (n) => headers.findIndex((h) => h.toLowerCase() === n.toLowerCase());
  const iSym = col('Symbol'), iLast = col('Last'), iPClose = col('P Close'),
        iChg = col('Change'), iVal = col('Value'), iVol = col('Volume');
  const board = {};
  for (const cells of rows) {
    const sym = (cells[iSym] || '').toUpperCase();
    if (!/^[A-Z0-9]{1,12}$/.test(sym)) continue;
    let price = num(cells[iLast]); if (!price) price = num(cells[iPClose]);
    const pct = num(cells[iChg]);
    if (price == null || pct == null) continue;
    board[sym] = { price, change_pct: +(pct / 100).toFixed(5), value: num(cells[iVal]),
                   volume: num(cells[iVol]), exchange: 'ADX', source: 'ADX (delayed)' };
  }
  // map registry ADX symbols (+aliases) onto the board, keyed by registry symbol
  let hit = 0;
  for (const t of adxTargets) {
    const code = [t.symbol, ...(t.aliases || [])].map((s) => s.toUpperCase()).find((s) => board[s]);
    if (code) { quotes[t.symbol] = board[code]; hit++; }
  }
  if (index) { const m = index.match(/([\d,]+\.\d+)\D+([\d.]+)\s*\(([-\d.]+)%/); if (m) indices.adx = { value: num(m[1]), change_pct: +(num(m[3]) / 100).toFixed(5) }; }
  console.error(`[scrape] ADX board: ${Object.keys(board).length} symbols, matched ${hit}/${adxTargets.length} registry, FADGI=${indices.adx?.value}`);
} catch (e) { console.error(`[scrape] ADX FAILED: ${e.message}`); }

// ---------------- DFM: per-symbol search autocomplete ----------------
try {
  await page.goto('https://marketwatch.dfm.ae/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(6000);
  // capture DFMGI index from the page
  const dfmIdx = await page.evaluate(() => {
    const hdr = [...document.querySelectorAll('*')].find((e) => {
      const t = (e.innerText || '').replace(/\s+/g, ' ').trim();
      return t.length < 70 && /dfmgi/i.test(t) && /\d,\d{3}\.\d/.test(t);
    });
    return hdr ? hdr.innerText.replace(/\s+/g, ' ').trim() : null;
  });
  if (dfmIdx) { const m = dfmIdx.match(/([\d,]+\.\d+)[^\d]*\(([-\d.]+)\s*\/\s*([-\d.]+)%/); if (m) indices.dfm = { value: num(m[1]), change_pct: +(num(m[3]) / 100).toFixed(5) }; }

  const inp = await page.$('input[placeholder*="Search by security"]');
  let hit = 0;
  for (const t of dfmTargets) {
    const candidates = [t.symbol, ...(t.aliases || [])];
    let got = null;
    for (const cand of candidates) {
      try {
        await inp.fill(''); await page.waitForTimeout(200);
        await inp.fill(cand); await page.waitForTimeout(1500);
        got = await page.evaluate((cand) => {
          // suggestion looks like "<SYM> <price> (<pct>%)" inside a .ticker-item with an
          // increase/decrease class. Find the first matching small element.
          const els = [...document.querySelectorAll('li,a,div,span')];
          for (const el of els) {
            const t = (el.innerText || '').trim().replace(/\s+/g, ' ');
            if (t.length >= 40 || el.childElementCount > 4) continue;
            if (!new RegExp('^' + cand + '\\b', 'i').test(t)) continue;
            const pm = t.match(/([\d.]+)\s*\(([-\d.]+)%\)/);
            if (!pm) continue;
            const html = (el.outerHTML || '').toLowerCase();
            const neg = /decrease|\bdown\b|\bred\b|loss|negative/.test(html);
            return { price: parseFloat(pm[1]), pct: parseFloat(pm[2]), neg };
          }
          return null;
        }, cand);
        if (got && Number.isFinite(got.price)) break;
      } catch (e) { /* try next alias */ }
    }
    if (got && Number.isFinite(got.price)) {
      const signed = (got.neg ? -Math.abs(got.pct) : Math.abs(got.pct)) / 100;
      quotes[t.symbol] = { price: got.price, change_pct: +signed.toFixed(5), value: null,
                           volume: null, exchange: 'DFM', source: 'DFM (delayed)' };
      hit++;
    }
  }
  console.error(`[scrape] DFM search: matched ${hit}/${dfmTargets.length} registry, DFMGI=${indices.dfm?.value}`);
} catch (e) { console.error(`[scrape] DFM FAILED: ${e.message}`); }

await browser.close();

const count = Object.keys(quotes).length;
mkdirSync(DATA, { recursive: true });
writeFileSync(OUT, JSON.stringify({
  generated_at: new Date().toISOString(),
  source: 'headless-chromium (ADX all-equities board + DFM marketwatch search)',
  delay: '~15min',
  count,
  indices,
  quotes,
}, null, 2));
console.error(`[scrape] wrote ${count} live quotes -> ${OUT}`);
if (count < 20) process.exit(2);
