import { chromium } from 'playwright';
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const targets = [
  ['ADX all-equities', 'https://www.adx.ae/all-equities'],
  ['DFM marketwatch', 'https://marketwatch.dfm.ae/'],
];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US', viewport: {width:1366,height:900} });
const page = await ctx.newPage();
for (const [name, url] of targets) {
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(6000); // let SPA + any challenge resolve
    const title = await page.title();
    const bodyLen = (await page.content()).length;
    const text = (await page.innerText('body')).slice(0, 0);
    // count numeric price-like cells + look for a known ticker
    const nums = await page.$$eval('*', els => {
      let c=0; for (const e of els){ const t=(e.childElementCount===0?e.textContent:'').trim(); if(/^\d{1,3}\.\d{2,3}$/.test(t)) c++; } return c;
    }).catch(()=>-1);
    const hasEmaar = (await page.content()).match(/EMAAR|Emaar|إعمار/) ? 'yes':'no';
    const hasCF = (await page.content()).match(/Just a moment|cf-browser-verification|Checking your browser|Cloudflare/i) ? 'CLOUDFLARE-CHALLENGE':'no-cf';
    console.log(`${name}: HTTP=${resp?.status()} title="${title.slice(0,40)}" bodyLen=${bodyLen} priceCells=${nums} emaar=${hasEmaar} cf=${hasCF}`);
  } catch(e){ console.log(`${name}: ERROR ${e.message.slice(0,80)}`); }
}
await browser.close();
