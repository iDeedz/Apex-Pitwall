const puppeteer=require('puppeteer-core');const W=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{const out={runs:{},fail:[]};
for(const [w,th] of [[1280,'night'],[1280,'day'],[768,'night'],[768,'day'],[390,'night'],[390,'day']]){
 const b=await puppeteer.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox']});const p=await b.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));p.on('console',m=>m.type()==='error'&&errs.push(m.text()));
 await p.setViewport({width:w,height:w<500?844:(w<900?1024:800)});await p.evaluateOnNewDocument(t=>{sessionStorage.setItem('ax_auth','1');localStorage.setItem('ax_theme',t)},th);
 await p.goto((process.env.BASE||(process.env.BASE||'http://127.0.0.1:8940/')+'')+'pitwall-bridge.html',{waitUntil:'networkidle0'});await p.evaluate(()=>{window.__mark=1;const d=document.querySelector('.ax-drivers');if(innerWidth>900)d.scrollTop=120;else d.scrollLeft=200});
 const R={swaps:0,reloads:0,loader:0,mismatch:[],errs};
 const links=await p.evaluate(()=>[...document.querySelectorAll('.ax-stint-link')].map(a=>a.getAttribute('href')));
 const more=await p.evaluate(()=>[...document.querySelectorAll('.ax-more-link')].map(a=>a.getAttribute('href')));
 const seq=[...links.slice(1),...more.filter((_,i)=>i%2===0)];
 for(const h of seq){const isMore=more.includes(h);if(isMore){await p.click('#axMoreBtn');await W(80)}
  const sel=(isMore?'.ax-more-link':'.ax-stint-link')+`[href="${h}"]`;
  await p.evaluate(s=>{const a=document.querySelector(s);a.scrollIntoView({block:'nearest',inline:'nearest'});},sel);await p.click(sel);
  await W(60);if(await p.evaluate(()=>!!document.querySelector('.ax-loader'))) R.loader++;
  await p.waitForFunction(()=>!document.querySelector('.ax-loader'),{timeout:8000}).catch(()=>{});await W(120);
  const s=await p.evaluate(h=>({mark:window.__mark,url:location.pathname.split('/').pop(),nav:performance.getEntriesByType('navigation').length,title:document.title,active:(document.querySelector('.ax-stint-link.active,.ax-more-link.active')||{}).getAttribute?.('href'),drv:innerWidth>900?document.querySelector('.ax-drivers').scrollTop:document.querySelector('.ax-drivers').scrollLeft,tracks:document.querySelectorAll('#trackCanvas').length}),h);
  R.swaps++;if(s.mark!==1)R.reloads++;if(s.url!==h||s.active!==h||!s.title)R.mismatch.push(h+' '+JSON.stringify(s));if(s.drv<100)R.mismatch.push('driver scroll lost on '+h+' '+s.drv);}
 // duplicate listener check: one click on a data-action button -> exactly one new toast
 await p.goto((process.env.BASE||(process.env.BASE||'http://127.0.0.1:8940/')+'')+'pitwall-bridge.html',{waitUntil:'networkidle0'});await p.evaluate(()=>window.__mark=2);
 for(const h of ['fuel-energy.html','tire-desk.html','pitwall-bridge.html','fuel-energy.html','pitwall-bridge.html']){await p.evaluate(h=>ApexSPA.go(h,true),h);await p.waitForFunction(h=>location.pathname.endsWith(h)&&!document.querySelector('.ax-loader'),{timeout:8000},h);await W(100)}
 R.dup=await p.evaluate(async()=>{document.querySelectorAll('.toast').forEach(t=>t.remove());const b=document.querySelector('main [data-action]')||document.querySelector('[data-track-filter="LIVE"]');b.click();await new Promise(r=>setTimeout(r,50));return document.querySelectorAll('.toast').length});
 R.trackCanvas=await p.evaluate(()=>!!window._axTrack&&window._axTrack.canvas.isConnected);
 R.energyAfterSwap=await p.evaluate(async()=>{ApexSPA.go('fuel-energy.html',true);await new Promise(r=>setTimeout(r,900));return document.querySelectorAll('#axEnergy svg polyline').length});
 await p.goBack();await W(900);R.back=await p.evaluate(()=>[window.__mark,location.pathname.split('/').pop(),!!document.querySelector('#trackCanvas')]);
 await p.goForward();await W(900);R.fwd=await p.evaluate(()=>[window.__mark,location.pathname.split('/').pop(),document.querySelectorAll('#axEnergy svg').length]);
 out.runs[w+th]=R;if(R.reloads||R.mismatch.length||errs.length||R.dup!==1||R.loader<R.swaps-1||R.back[0]!==2||R.back[1]!=='pitwall-bridge.html'||!R.back[2]||R.fwd[1]!=='fuel-energy.html'||!R.fwd[2])out.fail.push(w+th);await b.close();}
{const b=await puppeteer.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome',headless:'new',args:['--no-sandbox','--allow-file-access-from-files']});const p=await b.newPage();const errs=[];p.on('pageerror',e=>errs.push(e.message));await p.setViewport({width:1280,height:800});await p.evaluateOnNewDocument(()=>sessionStorage.setItem('ax_auth','1'));
 await p.goto('file://'+require('path').join(__dirname,'..')+'/pitwall-bridge.html',{waitUntil:'load'});await p.evaluate(()=>window.__mark=1);await Promise.all([p.waitForNavigation(),p.click('.ax-stint-link[href="sector-map.html"]')]);
 out.file=await p.evaluate(()=>({mark:window.__mark||0,url:location.pathname.split('/').pop(),main:!!document.querySelector('main.ax-stage')}));out.file.errs=errs;if(out.file.url!=='sector-map.html'||!out.file.main||errs.length)out.fail.push('file');
 const q=await b.newPage();await q.setViewport({width:1280,height:800});await q.evaluateOnNewDocument(()=>sessionStorage.setItem('ax_auth','1'));await q.goto((process.env.BASE||(process.env.BASE||'http://127.0.0.1:8940/')+'')+'sector-map.html?x=1',{waitUntil:'networkidle0'});out.deep=await q.evaluate(()=>[document.title,(document.querySelector('.ax-stint-link.active')||{}).textContent]);await b.close()}
console.log(JSON.stringify(out,null,1))})();
