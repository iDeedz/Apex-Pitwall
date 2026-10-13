// Apex Pitwall checker: hscroll, tower fit, HUD overlap, pixel contrast (text hidden -> median bg behind each text run), JS errors, links.
const puppeteer=require('puppeteer-core'),fs=require('fs'),path=require('path');
const ROOT=require('path').join(__dirname,'..')+'/',BASE=process.env.BASE||(process.env.BASE||'http://127.0.0.1:8940/')+'';
const only=process.env.PAGES?process.env.PAGES.split(','):null;
const pages=fs.readdirSync(ROOT).filter(f=>f.endsWith('.html')&&f!=='index.html'&&(!only||only.includes(f)));
const W=(process.env.W||'390,768,1280').split(',').map(Number),TH=(process.env.TH||'night,day').split(',');
const HIDE='*,*::before,*::after{color:transparent!important;-webkit-text-fill-color:transparent!important;text-shadow:none!important;caret-color:transparent!important}';
const NOANIM='*,*::before,*::after{animation:none!important;transition:none!important}';
async function run(b,pg,w,th){const p=await b.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>m.type()==='error'&&errs.push(m.text()));p.on('requestfailed',r=>errs.push('reqfail '+r.url()));
 await p.setViewport({width:w,height:w<500?844:(w<900?1024:800)});await p.evaluateOnNewDocument(t=>{sessionStorage.setItem('ax_auth','1');localStorage.setItem('ax_theme',t)},th);
 await p.goto(BASE+pg,{waitUntil:'networkidle0'});await p.addStyleTag({content:NOANIM});await new Promise(r=>setTimeout(r,350));
 const r={pg,w,th,errs,fails:[]};
 const lay=await p.evaluate(()=>{const o=[];const se=document.scrollingElement;if(se.scrollWidth>innerWidth+1)o.push('hscroll '+se.scrollWidth);
  const tw=document.querySelector('.ax-tower');if(tw){[...tw.querySelectorAll('.ax-lap-cell,.ax-tower-actions a,.ax-tower-actions button')].forEach(c=>{const x=c.getBoundingClientRect();if(x.width<4||x.left<-1||x.right>innerWidth+1||getComputedStyle(c).display==='none')o.push('tower hidden/clipped '+(c.textContent||c.title).trim().slice(0,20));
   c.querySelectorAll('div').forEach(d=>{if(d.scrollWidth>d.clientWidth+1)o.push('tower text clipped '+d.textContent)})});}
  const hud=document.querySelector('.ax-track-hud'),cv=document.querySelector('#trackCanvas');if(hud&&cv&&innerWidth<=900){const a=hud.getBoundingClientRect(),c=cv.getBoundingClientRect();if(Math.min(a.bottom,c.bottom)-Math.max(a.top,c.top)>2)o.push('hud covers track')}
  document.querySelectorAll('a[href]').forEach(a=>{const h=a.getAttribute('href');if(h==='#'||h==='')o.push('dead href')});
  const nav=document.querySelector('.ax-ticker');if(nav){const x=nav.getBoundingClientRect();if(x.bottom>innerHeight+1&&getComputedStyle(nav).position!=='sticky')o.push('nav not reachable')}
  return o});r.fails.push(...lay);
 await p.evaluate(()=>{window.__C=new Map();document.querySelectorAll('body *').forEach(e=>window.__C.set(e,getComputedStyle(e).color))});
 await p.addStyleTag({content:HIDE});
 // scroll positions: window (doc flow) or inner scrollers (desktop app shell)
 const scrollers=await p.evaluate(()=>{const s=[...document.querySelectorAll('.ax-stage,.ax-radio,.ax-drivers,.ax-more-sheet')].filter(e=>e.scrollHeight>e.clientHeight+4&&getComputedStyle(e).overflowY!=='visible');return {win:document.scrollingElement.scrollHeight>innerHeight+4,steps:Math.max(1,...s.map(e=>Math.ceil(e.scrollHeight/(e.clientHeight*0.85)))),wsteps:Math.ceil(document.scrollingElement.scrollHeight/(innerHeight*0.7))}});
 const N=Math.min(14,Math.max(scrollers.steps,scrollers.win?scrollers.wsteps:1));const low=new Map();
 for(let k=0;k<N;k++){
  await p.evaluate(k=>{document.querySelectorAll('.ax-stage,.ax-radio,.ax-drivers').forEach(e=>e.scrollTop=k*e.clientHeight*0.85);window.scrollTo(0,k*innerHeight*0.7)},k);await new Promise(r=>setTimeout(r,60));
  const shot=await p.screenshot({encoding:'base64'});if(process.env.DUMP)require('fs').writeFileSync(require('os').tmpdir()+'/ax-dump-'+k+'.png',Buffer.from(shot,'base64'));
  const res=await p.evaluate(async(b64)=>{const img=new Image();img.src='data:image/png;base64,'+b64;await img.decode();const c=document.createElement('canvas');c.width=img.width;c.height=img.height;const x=c.getContext('2d');x.drawImage(img,0,0);const sx=img.width/innerWidth;
   function lum(r,g,b){const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(r)+.7152*f(g)+.0722*f(b)}
   const out=[];const tw=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
   while(n=tw.nextNode()){const t=n.nodeValue.trim();if(!t)continue;const el=n.parentElement;if(!el||el.closest('script,style,noscript,canvas,svg,option,select')) continue;
    const cs=getComputedStyle(el);if(cs.visibility==='hidden'||cs.display==='none')continue;let op=1,e=el;while(e){op*=+getComputedStyle(e).opacity;e=e.parentElement}if(op<0.05)continue;
    const rg=document.createRange();rg.selectNodeContents(n);const rects=[...rg.getClientRects()].filter(q=>q.width>2&&q.height>4&&q.bottom>0&&q.top<innerHeight&&q.right>0&&q.left<innerWidth);if(!rects.length)continue;
    let q=rects[0];{let L=q.left,T=q.top,Rr=q.right,Bb=q.bottom,an=el.parentElement;while(an&&an!==document.body){const oc=getComputedStyle(an);if(oc.overflowX!=='visible'||oc.overflowY!=='visible'){const ar=an.getBoundingClientRect();L=Math.max(L,ar.left);T=Math.max(T,ar.top);Rr=Math.min(Rr,ar.right);Bb=Math.min(Bb,ar.bottom)}an=an.parentElement}if(Rr-L<3||Bb-T<4)continue;q={left:L,top:T,right:Rr,bottom:Bb,width:Rr-L,height:Bb-T}}const cx=Math.min(innerWidth-1,Math.max(0,q.left+q.width/2)),cy=Math.min(innerHeight-1,Math.max(0,q.top+q.height/2));const hit=document.elementFromPoint(cx,cy);if(!hit||!(hit===el||el.contains(hit)||hit.contains(el)))continue;
    const X0=Math.max(0,Math.floor(q.left*sx)),Y0=Math.max(0,Math.floor(q.top*sx)),X1=Math.min(img.width,Math.ceil(q.right*sx)),Y1=Math.min(img.height,Math.ceil(q.bottom*sx));if(X1-X0<1||Y1-Y0<1)continue;
    const d=x.getImageData(X0,Y0,X1-X0,Y1-Y0).data;const R=[],G=[],B=[];for(let i=0;i<d.length;i+=16){R.push(d[i]);G.push(d[i+1]);B.push(d[i+2])}const med=a=>a.sort((u,v)=>u-v)[a.length>>1];const br=med(R),bg=med(G),bb=med(B);
    const m=(window.__C.get(el)||cs.color).match(/[\d.]+/g).map(Number);const a=(m[3]==null?1:m[3])*op;const fr=m[0]*a+br*(1-a),fg=m[1]*a+bg*(1-a),fb=m[2]*a+bb*(1-a);
    const L1=lum(fr,fg,fb),L2=lum(br,bg,bb);const ratio=(Math.max(L1,L2)+.05)/(Math.min(L1,L2)+.05);const fs=parseFloat(cs.fontSize),bold=+cs.fontWeight>=700;const need=(fs>=24||(fs>=18.66&&bold))?3:4.5;
    if(ratio<need)out.push({t:t.slice(0,30),ratio:+ratio.toFixed(2),fg:(window.__C.get(el)||cs.color),bg:`rgb(${br},${bg},${bb})`,cls:(el.className||el.tagName).toString().slice(0,40),y:Math.round(q.top),x:Math.round(q.left),sy:scrollY})}
   return out},shot);
  res.forEach(f=>{const k=f.t+'|'+f.cls;if(!low.has(k))low.set(k,f)});
 }
 r.contrast=[...low.values()];await p.close();return r}
(async()=>{const b=await puppeteer.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});
 const jobs=[];for(const pg of pages)for(const w of W)for(const th of TH)jobs.push([pg,w,th]);const out=[];let i=0;
 await Promise.all([0,1,2].map(async()=>{const b=await puppeteer.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});while(i<jobs.length){const j=jobs[i++];let tm;try{out.push(await Promise.race([run(b,...j),new Promise((_,rej)=>{tm=setTimeout(()=>rej(new Error('timeout 90s')),90000)})]));clearTimeout(tm)}catch(e){clearTimeout(tm);out.push({pg:j[0],w:j[1],th:j[2],fails:['crash '+e.message],contrast:[],errs:[]})}}await b.close()}));
 await b.close();
 const T={contrast:0,layout:0,errs:0};out.forEach(r=>{T.contrast+=r.contrast.length;T.layout+=r.fails.length;T.errs+=r.errs.length});
 fs.writeFileSync(path.join(__dirname,'results.json'),JSON.stringify(out,null,1));
 const bad=out.filter(r=>r.contrast.length||r.fails.length||r.errs.length);console.log(JSON.stringify({checks:out.length,failing:bad.length,totals:T},null,1));
 const agg={};out.forEach(r=>r.contrast.forEach(c=>{const k=c.cls+' | '+c.fg+' on '+c.bg;agg[k]=agg[k]||{n:0,ex:c.t,pg:r.pg+'@'+r.w+r.th,ratio:c.ratio};agg[k].n++}));
 Object.entries(agg).sort((a,b)=>b[1].n-a[1].n).slice(0,40).forEach(([k,v])=>console.log(v.n,k,'|',v.ex,v.ratio,v.pg));
 const lf={};out.forEach(r=>[...r.fails,...r.errs].forEach(f=>{const k=f.replace(/\d+/g,'#');lf[k]=lf[k]||[];lf[k].push(r.pg+'@'+r.w+r.th)}));Object.entries(lf).forEach(([k,v])=>console.log('L',v.length,k,v.slice(0,4).join(' ')));
})();
