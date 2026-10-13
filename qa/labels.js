// Track-canvas label overlap check: samples ApexTrack label boxes over time on every page with #trackCanvas
// at 390/768/1280 in both themes. Fails on any sector-vs-car or car-vs-car label intersection.
const puppeteer=require('puppeteer-core'),fs=require('fs'),path=require('path');
const ROOT=path.join(__dirname,'..'),BASE=process.env.BASE||(process.env.BASE||'http://127.0.0.1:8940/')+'';
const pages=fs.readdirSync(ROOT).filter(f=>f.endsWith('.html')&&fs.readFileSync(path.join(ROOT,f),'utf8').includes('id="trackCanvas"'));
(async()=>{const b=await puppeteer.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});const fails=[];let samples=0;
for(const pg of pages)for(const w of [390,768,1280])for(const th of ['night','day']){const p=await b.newPage();
 await p.setViewport({width:w,height:w<500?844:(w<900?1024:800)});await p.evaluateOnNewDocument(t=>{sessionStorage.setItem('ax_auth','1');localStorage.setItem('ax_theme',t)},th);
 await p.goto(BASE+pg,{waitUntil:'networkidle0'});
 for(let k=0;k<30;k++){await new Promise(r=>setTimeout(r,250));
  const o=await p.evaluate(()=>{const T=window._axTrack;if(!T||!T._labels)return null;const L=T._labels,out=[];
   for(let i=0;i<L.length;i++)for(let j=i+1;j<L.length;j++){const a=L[i],c=L[j];if(a.x<c.x+c.w&&c.x<a.x+a.w&&a.y<c.y+c.h&&c.y<a.y+a.h)out.push(a.t+' vs '+c.t)}
   L.forEach(a=>{if(a.x<0||a.y<0||a.x+a.w>T.w||a.y+a.h>T.h)out.push('off-canvas '+a.t)});return out});
  if(o===null){fails.push(pg+' '+w+' no labels');break}samples++;o.forEach(x=>fails.push(`${pg} ${w} ${th}: ${x}`));}
 await p.close()}
const uniq=[...new Set(fails)];console.log(JSON.stringify({pages,samples,fails:uniq.length,list:uniq.slice(0,40)},null,1));await b.close();process.exit(uniq.length?1:0)})();
