// Spark text-collision check: every spark canvas (pace/fuel/wear) on every page at 390/768/1280, both themes.
// Fails on any overlapping text boxes, text outside the canvas, or a canvas clipped by its container.
const puppeteer=require('puppeteer-core'),fs=require('fs'),path=require('path');
const ROOT=path.join(__dirname,'..'),BASE=process.env.BASE||'http://127.0.0.1:8940/';
const pages=fs.readdirSync(ROOT).filter(f=>f.endsWith('.html')&&/id="spark(Pace|Fuel|Wear)"/.test(fs.readFileSync(path.join(ROOT,f),'utf8')));
(async()=>{const b=await puppeteer.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});const fails=[];let n=0;
for(const pg of pages)for(const w of [390,768,1280])for(const th of ['night','day']){const p=await b.newPage();
 await p.setViewport({width:w,height:w<500?844:(w<900?1024:800)});await p.evaluateOnNewDocument(t=>{sessionStorage.setItem('ax_auth','1');localStorage.setItem('ax_theme',t)},th);
 await p.goto(BASE+pg,{waitUntil:'networkidle0'});await new Promise(r=>setTimeout(r,300));
 const o=await p.evaluate(()=>{const out=[];let n=0;document.querySelectorAll('canvas[id^=spark]').forEach(c=>{if(!c.offsetParent)return;const L=c.__labels;if(!L){out.push(c.id+' not drawn');return}n++;
  const cw=parseFloat(c.style.width),ch=parseFloat(c.style.height),pr=c.parentElement.getBoundingClientRect();
  if(ch>pr.height+1||cw>pr.width+1)out.push(c.id+' canvas clipped by container');
  for(let i=0;i<L.length;i++){const a=L[i];if(a.x<0||a.y<0||a.x+a.w>cw||a.y+a.h>ch)out.push(c.id+' off-canvas '+a.t);
   for(let j=i+1;j<L.length;j++){const d=L[j];if(a.x<d.x+d.w&&d.x<a.x+a.w&&a.y<d.y+d.h&&d.y<a.y+a.h)out.push(c.id+': '+a.t+' x '+d.t)}}});return {out,n}});
 n+=o.n;o.out.forEach(x=>fails.push(`${pg} ${w} ${th} ${x}`));await p.close()}
console.log(JSON.stringify({pages:pages.length,sparks:n,fails:fails.length,list:fails.slice(0,40)},null,1));await b.close();process.exit(fails.length?1:0)})();
