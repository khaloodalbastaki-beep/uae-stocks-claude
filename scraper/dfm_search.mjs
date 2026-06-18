import { chromium } from 'playwright';
const UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const browser=await chromium.launch({headless:true});
const ctx=await browser.newContext({userAgent:UA,locale:'en-US',viewport:{width:1400,height:1000}});
const page=await ctx.newPage();
await page.goto('https://marketwatch.dfm.ae/',{waitUntil:'domcontentloaded',timeout:40000});
await page.waitForTimeout(6000);
// find inputs
const inputs=await page.$$eval('input', els=>els.map(e=>({ph:e.placeholder||'',type:e.type,name:e.name||'',id:e.id||''})).slice(0,10));
console.log('inputs:', JSON.stringify(inputs));
// try typing DEWA into the first text/search input
const inp=await page.$('input[type="search"], input[type="text"], input:not([type])');
if(inp){
  await inp.fill('DEWA'); await page.waitForTimeout(2500);
  // read any dropdown/autocomplete suggestions
  const sugg=await page.$$eval('[class*="suggest"],[class*="result"],[class*="dropdown"],li,a', els=>els.map(e=>(e.innerText||'').trim().replace(/\s+/g,' ')).filter(t=>/DEWA/i.test(t)).slice(0,5));
  console.log('DEWA suggestions:', JSON.stringify(sugg));
} else console.log('no input found');
await browser.close();
