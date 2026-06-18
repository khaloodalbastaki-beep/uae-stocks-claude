import { chromium } from 'playwright';
const UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const browser=await chromium.launch({headless:true});
const ctx=await browser.newContext({userAgent:UA,locale:'en-US',viewport:{width:1500,height:1100}});
const page=await ctx.newPage();
const urls=[
  'https://www.dfm.ae/en/the-exchange/market-information/listed-securities/equities',
  'https://www.dfm.ae/the-exchange/market-information/listed-securities/equities',
];
for(const url of urls){
  try{
    const r=await page.goto(url,{waitUntil:'domcontentloaded',timeout:40000});
    await page.waitForTimeout(6000);
    const rows=await page.$$eval('tr', trs=>trs.map(tr=>Array.from(tr.querySelectorAll('th,td')).map(c=>c.innerText.trim().replace(/\s+/g,' ')).filter(Boolean)).filter(c=>c.length>=3).slice(0,5));
    const cf=(await page.content()).match(/Just a moment|Checking your browser/i)?'CF':'ok';
    console.log(`\n${url}\n HTTP=${r?.status()} cf=${cf} sampleRows=${rows.length}`);
    rows.forEach((c,i)=>console.log(`  [${i}] ${JSON.stringify(c).slice(0,160)}`));
  }catch(e){console.log(url,'ERR',e.message.slice(0,60));}
}
await browser.close();
