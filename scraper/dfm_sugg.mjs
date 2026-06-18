import { chromium } from 'playwright';
const UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const browser=await chromium.launch({headless:true});
const ctx=await browser.newContext({userAgent:UA,locale:'en-US',viewport:{width:1400,height:1000}});
const page=await ctx.newPage();
await page.goto('https://marketwatch.dfm.ae/',{waitUntil:'domcontentloaded',timeout:40000});
await page.waitForTimeout(6000);
const inp=await page.$('input[placeholder*="Search by security"]');
for(const sym of ['DEWA','SALIK','GFH']){  // GFH was up? mix of up/down to test sign
  await inp.fill(''); await page.waitForTimeout(300); await inp.fill(sym); await page.waitForTimeout(2000);
  const data=await page.evaluate((sym)=>{
    // find a small element whose text starts with the symbol and has a price
    const cand=[...document.querySelectorAll('li,a,div,span')].filter(e=>{
      const t=(e.innerText||'').trim(); return e.childElementCount<=4 && new RegExp('^'+sym+'\\b').test(t) && /\d+\.\d{2,3}/.test(t) && t.length<40;
    });
    if(!cand.length) return null;
    const e=cand[0];
    const color=getComputedStyle(e).color;
    // also check descendants' colors
    const childColors=[...e.querySelectorAll('*')].map(c=>getComputedStyle(c).color).slice(0,4);
    return {text:e.innerText.trim().replace(/\s+/g,' '), color, childColors, html:e.outerHTML.slice(0,180)};
  }, sym);
  console.log(sym, '->', JSON.stringify(data));
}
await browser.close();
