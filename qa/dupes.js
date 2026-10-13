// Duplicate stat-card sweep: on every page, collect each row of stat cards (.kpi-card / gauge tiles) in <main>
// and fail if a stat label (or label+value) appears in more than one row, or twice in one row.
const puppeteer=require('puppeteer-core'),fs=require('fs'),path=require('path');
const ROOT=path.join(__dirname,'..'),BASE=process.env.BASE||'http://127.0.0.1:8940/';
const pages=fs.readdirSync(ROOT).filter(f=>f.endsWith('.html')&&f!=='index.html');
const norm=s=>s.replace(/\s+/g,' ').trim().toLowerCase();
(async()=>{const b=await puppeteer.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});const fails=[];let rows=0;
for(const pg of pages){const p=await b.newPage();await p.setViewport({width:1280,height:800});await p.evaluateOnNewDocument(()=>sessionStorage.setItem('ax_auth','1'));
 await p.goto(BASE+pg,{waitUntil:'networkidle0'});
 const R=await p.evaluate(()=>{const m=document.querySelector('main')||document.body;const groups=new Map();
  m.querySelectorAll('.kpi-card').forEach(c=>{const g=c.parentElement;if(!groups.has(g))groups.set(g,[]);const l=c.querySelector('.label'),v=c.querySelector('.value');if(l)groups.get(g).push([l.textContent,v?v.textContent:'',(c.querySelector('.meta')||{}).textContent||'']);});
  return [...groups.values()]});
 rows+=R.length;const seen=new Map(),vals=new Map();
 R.forEach((row,ri)=>{const inRow=new Set();row.forEach(([l,v,mt],ci)=>{const k=norm(l);if(!k)return;
  // sub-field sweep: a value, meta or code token must not appear in two different cards on the page
  const toks=new Set();[v,mt].forEach(x=>{const t=norm(x);if(t&&t!=='—'&&!/^\d+$/.test(t)&&!['sets','laps','ready','open'].includes(t))toks.add(t);[...(x.match(/\b[A-Z]{2,4}(?:-\d{2,3})?\b/g)||[]),...(x.match(/\d+(?:\.\d+)?\s?(?:%|C\b|kts|psi|km|s\b|laps)|\d:\d\d\.\d{3}/g)||[])].forEach(z=>{z=norm(z);if(z.length>=3)toks.add(z)})});
  toks.forEach(t=>{const id=ri+':'+ci;if(vals.has(t)&&vals.get(t).id!==id)fails.push(`${pg}: "${t}" repeats in cards "${vals.get(t).l}" and "${l}"`);else if(!vals.has(t))vals.set(t,{id,l})});
  if(inRow.has(k))fails.push(`${pg}: label "${l}" twice in row ${ri+1}`);inRow.add(k);
  if(seen.has(k))fails.push(`${pg}: "${l}" (${v.trim()}) repeats row ${seen.get(k)+1} -> row ${ri+1}`);else seen.set(k,ri)})});
 await p.close()}
console.log(JSON.stringify({pages:pages.length,rows,fails:fails.length,list:fails},null,1));await b.close();process.exit(fails.length?1:0)})();
