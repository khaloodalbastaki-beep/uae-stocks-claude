import { chromium } from 'playwright';
const UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36';
const browser=await chromium.launch({headless:true});
const ctx=await browser.newContext({userAgent:UA,locale:'en-US',viewport:{width:1440,height:1200}});
const page=await ctx.newPage();
await page.goto('https://www.adx.ae/all-equities',{waitUntil:'domcontentloaded',timeout:40000});
await page.waitForTimeout(8000);
// find repeating row containers: elements whose text has a TICKER and a price
const info=await page.evaluate(()=>{
  const out=[];
  const all=document.querySelectorAll('a,div,li');
  const seen={};
  for(const e of all){
    const t=e.innerText||'';
    // a row likely has a short ticker line + a price like 8.830 + a % 
    if(/\b[A-Z]{2,8}\b/.test(t) && /\d+\.\d{2,3}/.test(t) && /%/.test(t) && t.length<120){
      const cls=e.className&&e.className.baseVal!==undefined?e.className.baseVal:(e.className||'');
      const key=(typeof cls==='string'?cls:'').split(' ').slice(0,2).join('.');
      seen[key]=(seen[key]||0)+1;
      if(out.length<4) out.push({cls:(typeof cls==='string'?cls:'').slice(0,60), text:t.replace(/\s+/g,' ').slice(0,90)});
    }
  }
  const top=Object.entries(seen).sort((a,b)=>b[1]-a[1]).slice(0,6);
  return {samples:out, classCounts:top};
});
console.log('class counts (repeating row candidates):', JSON.stringify(info.classCounts));
console.log('samples:'); info.samples.forEach(s=>console.log(`  [${s.cls}] ${s.text}`));
await browser.close();
