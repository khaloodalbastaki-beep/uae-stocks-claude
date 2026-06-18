import { chromium } from 'playwright';
const UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const browser=await chromium.launch({headless:true});
const ctx=await browser.newContext({userAgent:UA,locale:'en-US',viewport:{width:1500,height:1100}});
const page=await ctx.newPage();
await page.goto('https://marketwatch.dfm.ae/',{waitUntil:'domcontentloaded',timeout:40000});
await page.waitForTimeout(7000);
// tabs / filters / market selectors
const tabs=await page.$$eval('a,button,li,option,[role="tab"]', els=>{
  const s=new Set();
  for(const e of els){const t=(e.innerText||'').trim().replace(/\s+/g,' ');
    if(t && t.length<28 && /equit|market|all|main|spot|share|secur/i.test(t)) s.add(t);}
  return [...s].slice(0,25);
});
console.log('candidate tabs/filters:', JSON.stringify(tabs));
// how many spot (non-future) symbols visible now
const rows=await page.$$eval('tr', trs=>trs.map(tr=>(tr.querySelector('th,td')?.innerText||'').trim().replace(/\s+/g,'')).filter(s=>/^[A-Z]{2,8}$/.test(s)));
console.log('spot-looking symbols in default table:', JSON.stringify([...new Set(rows)].slice(0,40)));
await browser.close();
