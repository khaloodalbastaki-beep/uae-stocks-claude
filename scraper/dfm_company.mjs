import { chromium } from 'playwright';
const UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const browser=await chromium.launch({headless:true});
const ctx=await browser.newContext({userAgent:UA,locale:'en-US',viewport:{width:1400,height:1000}});
const page=await ctx.newPage();
// 1) what does clicking a symbol on marketwatch lead to?
await page.goto('https://marketwatch.dfm.ae/',{waitUntil:'domcontentloaded',timeout:40000});
await page.waitForTimeout(6000);
const links=await page.$$eval('a', as=>as.map(a=>a.href).filter(h=>/dfm\.ae/.test(h) && /(company|security|symbol|stock|equit|profile|detail|code=)/i.test(h)));
console.log('symbol-ish links:', JSON.stringify([...new Set(links)].slice(0,8)));
// 2) probe candidate company URLs for DEWA
const cands=[
 'https://www.dfm.ae/en/the-exchange/market-information/company/DEWA/financial-statements',
 'https://www.dfm.ae/en/market-data/company-data?code=DEWA',
 'https://marketwatch.dfm.ae/?symbol=DEWA',
 'https://www.dfm.ae/en/the-exchange/company-disclosures?companyCode=DEWA',
];
for(const u of cands){
  try{const r=await page.goto(u,{waitUntil:'domcontentloaded',timeout:25000});await page.waitForTimeout(3000);
    const hasPrice=(await page.content()).match(/\b\d+\.\d{2,3}\b/)?'price?':'no-num';
    console.log(`${r?.status()} ${hasPrice} ${u}`);}catch(e){console.log('ERR',u,e.message.slice(0,40));}
}
await browser.close();
