/* Render one URL to visible text via headless Chromium (gets past JS/Cloudflare that
 * plain HTTP can't). Used by Mizan's Gemini-free grounding: fetch the real filing/IR page,
 * print its text, and let gpt-oss:120b extract the reported figures from it.
 * Usage: node fetch_page.mjs "<url>"  -> prints up to ~9000 chars of body text to stdout. */
import { chromium } from 'playwright';

const url = process.argv[2];
if (!url) { process.stderr.write('no url\n'); process.exit(1); }
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';

const browser = await chromium.launch({ headless: true });
try {
  const ctx = await browser.newContext({ userAgent: UA, locale: 'en-US', viewport: { width: 1366, height: 1000 } });
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 35000 });
  await page.waitForTimeout(3500);
  let text = await page.innerText('body').catch(() => '');
  text = (text || '').replace(/\n{3,}/g, '\n\n').replace(/[ \t]{2,}/g, ' ').trim().slice(0, 9000);
  process.stdout.write(text);
} catch (e) {
  process.stderr.write('ERR ' + (e && e.message ? e.message : e));
  process.exit(2);
} finally {
  await browser.close();
}
