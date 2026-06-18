import { chromium } from 'playwright';
const UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const browser=await chromium.launch({headless:true});
const ctx=await browser.newContext({userAgent:UA,locale:'en-US',viewport:{width:1400,height:1000}});
const page=await ctx.newPage();
async function dumpRows(name,url){
  await page.goto(url,{waitUntil:'domcontentloaded',timeout:35000});
  await page.waitForTimeout(7000);
  // try to find the densest <tr> table
  const rows=await page.$$eval('tr', trs=>{
    return trs.map(tr=>Array.from(tr.querySelectorAll('th,td')).map(c=>c.innerText.trim().replace(/\s+/g,' ')).filter(Boolean))
      .filter(cells=>cells.length>=3).slice(0,6);
  }).catch(e=>['ERR '+e.message]);
  console.log(`\n=== ${name} : ${rows.length} sample rows ===`);
  rows.forEach((r,i)=>console.log(`  [${i}] ${JSON.stringify(r).slice(0,180)}`));
}
await dumpRows('ADX','https://www.adx.ae/all-equities');
await dumpRows('DFM','https://marketwatch.dfm.ae/');
await browser.close();
