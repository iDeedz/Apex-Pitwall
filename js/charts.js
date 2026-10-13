(function(){
  function cssv(v,f){return getComputedStyle(document.documentElement).getPropertyValue(v).trim()||f;}
  // spark with y-axis (min/mid/max), lap x-axis, unit labels and the latest value
  // spark with y-axis (min/mid/max), lap x-axis, title and latest value. Layout is collision-aware:
  // the title row is dropped below the value when they would meet, and y ticks are thinned until they have a gap.
  function spark(id, color, pts, o){ document.querySelectorAll('canvas[id="'+id+'"]').forEach(c=>sparkOne(c, color, pts, o)); }
  function sparkOne(c, color, pts, o){
    const ctx = c.getContext("2d");
    const dpr = Math.min(devicePixelRatio||1,2);
    const w = c.parentElement.clientWidth || 200, h = Math.max(96, c.parentElement.clientHeight || 120);
    c.width = w*dpr; c.height = h*dpr; c.style.width=w+"px"; c.style.height=h+"px";
    ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,w,h);
    const ink=cssv("--ax-ink","#F4F6FB"), mut=cssv("--ax-muted","#9AA3B8"), grid=cssv("--ax-line-soft","rgba(127,127,127,.18)");
    const boxes=[]; const put=(t,x,y,align,font,col)=>{ctx.font=font;ctx.textAlign=align;ctx.textBaseline="top";ctx.fillStyle=col;const tw=ctx.measureText(t).width,x0=align==="right"?x-tw:x;ctx.fillText(t,x,y);boxes.push({t,x:x0,y,w:tw,h:12});};
    let min=Math.min(...pts), max=Math.max(...pts); if(o.min!=null) min=o.min; if(o.max!=null) max=o.max; if(max===min) max=min+1;
    const TF="10px ui-monospace,monospace", VF="bold 11px ui-monospace,monospace";
    ctx.font=TF; const titleW=ctx.measureText(o.label).width; ctx.font=VF; const nowTxt="now "+o.fmt(pts[pts.length-1]), nowW=ctx.measureText(nowTxt).width;
    ctx.font=TF; const lw=Math.max(...[min,(min+max)/2,max].map(v=>ctx.measureText(o.fmt(v)).width));
    const stack = Math.ceil(lw) + 10 + titleW + 16 + nowW + 10 > w;   // narrow rail: title on row 1, value on row 2
    const top = stack ? 32 : 18;
    const P={l:Math.ceil(lw)+10,r:10,t:top+4,b:18}, iw=w-P.l-P.r, ih=h-P.t-P.b;
    const X=i=>P.l+(i/(pts.length-1))*iw, Y=v=>P.t+ih-((v-min)/(max-min))*ih;
    const ticks = ih >= 3*12+12 ? [max,(min+max)/2,min] : [max,min];   // need >=12px gap between tick labels
    ticks.forEach(v=>{ctx.strokeStyle=grid;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(P.l,Y(v));ctx.lineTo(w-P.r,Y(v));ctx.stroke();put(o.fmt(v),P.l-5,Y(v)-6,"right",TF,mut);});
    ctx.strokeStyle=mut; ctx.beginPath(); ctx.moveTo(P.l,P.t); ctx.lineTo(P.l,P.t+ih); ctx.lineTo(w-P.r,P.t+ih); ctx.stroke();
    put("L"+o.x0,P.l,P.t+ih+4,"left",TF,mut); put("L"+(o.x0+pts.length-1)+" · lap",w-P.r,P.t+ih+4,"right",TF,mut);
    ctx.beginPath(); pts.forEach((v,i)=>{ i?ctx.lineTo(X(i),Y(v)):ctx.moveTo(X(i),Y(v)); });
    ctx.strokeStyle=color; ctx.lineWidth=2; ctx.lineJoin="round"; ctx.stroke();
    ctx.fillStyle=color; ctx.beginPath(); ctx.arc(X(pts.length-1),Y(pts[pts.length-1]),3.5,0,Math.PI*2); ctx.fill();
    put(o.label,stack?0:P.l,2,"left",TF,mut);
    put(nowTxt,w-P.r,stack?16:2,"right",VF,ink);
    c.__labels=boxes;
    c.setAttribute("role","img"); c.setAttribute("aria-label",o.label+", now "+o.fmt(pts[pts.length-1]));
  }
  function mmss(v){const m=Math.floor(v/60),s=(v-m*60).toFixed(3);return m+":"+(s<10?"0":"")+s;}
  window.ApexCharts = {
    mount(){
      const D=window.AX_DATA||{kpis:{lap:38},drivers:[]}, E=window.AX_EXTRA||{laps:[]}, now=(D.kpis&&D.kpis.lap)||38;
      const v=(D.drivers||[]).find(d=>d.code==="VEX")||{fuel_pct:47,wear:61};
      const laps=E.laps.filter(l=>l.driver==="VEX"&&l.lap<=now).slice(-24);
      const x0=laps.length?laps[0].lap:now-23;
      const pace=laps.map(l=>l.t);
      const cy=cssv("--ax-cyan-t","#3DDCFF"), ne=cssv("--ax-neon-t","#FF2D55"), am=cssv("--ax-amber-t","#FFC107");
      if(pace.length>1) spark("sparkPace", ne, pace, {label:"#11 lap time",fmt:mmss,x0});
      const fuel=Array.from({length:24},(_,i)=>{const l=now-23+i;return +(100-(100-v.fuel_pct)*l/now).toFixed(1);});
      spark("sparkFuel", cy, fuel, {label:"#11 fuel %",fmt:x=>x.toFixed(0)+"%",x0:now-23});
      // current SOFT stint from L27: wear climbs to the live value
      const st=27, wear=Array.from({length:now-st+1},(_,i)=>+(v.wear*i/(now-st)).toFixed(1));
      spark("sparkWear", am, wear, {label:"#11 tyre wear %",fmt:x=>x.toFixed(0)+"%",x0:st,min:0});
    }
  };
})();
/* Energy timeline (fuel-energy.html): fuel % for #11 and #27, ERS charge for #11, stint bands, pit stops,
 * fuel-save window, 'now' marker and projection to the flag. Values end exactly on AX_DATA at lap 38. */
(function(){
  var NS="http://www.w3.org/2000/svg";
  function css(v){return getComputedStyle(document.documentElement).getPropertyValue(v).trim();}
  function series(D){
    var k=D.kpis, L=k.total_laps, now=k.lap, v=D.drivers.find(function(d){return d.code==="VEX";}), n=D.drivers.find(function(d){return d.code==="NOX";});
    function fuel(end,save){var out=[],rate=(100-end)/now;for(var i=0;i<=L;i++){var f=100-rate*i;if(save&&i>31&&i<=now)f+=0;out.push(+Math.max(0,f).toFixed(1));}return out;}
    var ers=[];for(var i=0;i<=L;i++){var e=70+18*Math.sin(i*0.55)+(i%7===3?-14:0);ers.push(Math.round(Math.max(18,Math.min(100,e))));}
    ers[now]=v.ers; // land exactly on the live value
    // stint bands and pit markers come from the derived stint book (tools/derive.py)
    var st=D.stints.filter(function(s){return s.driver==="VEX"&&s.status!=="Queued";});
    return {L:L,now:now,f11:fuel(v.fuel_pct),f27:fuel(n.fuel_pct),ers:ers,
      stints:st.map(function(s){return {a:s.from-1,b:s.to,c:s.compound};}),
      pits:st.slice(1).map(function(s,i){var ab={SOFT:"SOFT",MEDIUM:"MED",HARD:"HARD",INTER:"INT",WET:"WET"};return {l:st[i].to,t:"BOX · "+ab[st[i].compound]+"→"+ab[s.compound]};}),save:{a:31,b:36}};
  }
  function el(t,a,txt){var e=document.createElementNS(NS,t);for(var k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e;}
  function energy(){
    var host=document.getElementById("axEnergy");if(!host||!window.AX_DATA)return;
    var S=series(window.AX_DATA),W=Math.max(300,host.clientWidth||800),narrow=W<560,H=narrow?300:320,
      P={l:narrow?34:44,r:narrow?10:16,t:narrow?54:40,b:34},iw=W-P.l-P.r,ih=H-P.t-P.b;
    var ink=css("--ax-ink"),mut=css("--ax-muted"),grid=css("--ax-line-soft")||"rgba(255,255,255,.08)",cy=css("--ax-cyan-t"),li=css("--ax-lime-t"),ne=css("--ax-neon-t"),am=css("--ax-amber-t");
    var X=function(l){return P.l+iw*l/S.L;},Y=function(v){return P.t+ih*(1-v/100);};
    var svg=el("svg",{viewBox:"0 0 "+W+" "+H,width:W,height:H,class:"ax-energy-svg"});
    // stint bands
    var band={MEDIUM:"rgba(255,193,7,.10)",HARD:"rgba(200,206,220,.10)",SOFT:"rgba(255,107,61,.12)"};
    S.stints.forEach(function(s){svg.appendChild(el("rect",{x:X(s.a),y:P.t,width:X(s.b)-X(s.a),height:ih,fill:band[s.c]}));
      svg.appendChild(el("text",{x:(X(s.a)+X(s.b))/2,y:P.t+ih-26,"text-anchor":"middle","font-size":10,"font-weight":800,fill:mut,"letter-spacing":".08em"},"S"+(S.stints.indexOf(s)+1)+" "+s.c));});
    svg.appendChild(el("rect",{x:X(S.now),y:P.t,width:X(S.L)-X(S.now),height:ih,fill:"rgba(127,127,127,.07)"}));
    svg.appendChild(el("rect",{x:X(S.save.a),y:P.t+ih-18,width:X(S.save.b)-X(S.save.a),height:18,fill:"rgba(61,220,255,.16)"}));
    svg.appendChild(el("text",{x:(X(S.save.a)+X(S.save.b))/2,y:P.t+ih-5,"text-anchor":"middle","font-size":9.5,"font-weight":700,fill:cy},narrow?"save":"fuel save −0.2/lap"));
    // grid + axes
    for(var v=0;v<=100;v+=25){svg.appendChild(el("line",{x1:P.l,x2:W-P.r,y1:Y(v),y2:Y(v),stroke:grid}));svg.appendChild(el("text",{x:P.l-6,y:Y(v)+3.5,"text-anchor":"end","font-size":10,fill:mut},v+"%"));}
    var step=narrow?10:5;for(var l=0;l<=S.L;l+=step){svg.appendChild(el("text",{x:X(l),y:H-P.b+16,"text-anchor":"middle","font-size":10,fill:mut},"L"+l));}
    svg.appendChild(el("text",{x:W-P.r,y:H-4,"text-anchor":"end","font-size":10,fill:mut},"lap"));
    svg.appendChild(el("line",{x1:P.l,x2:W-P.r,y1:Y(0),y2:Y(0),stroke:mut,"stroke-width":1}));
    // lines: solid to now, dashed projection
    function line(vals,color,w){var a="",b="";vals.forEach(function(v,i){var pt=X(i).toFixed(1)+","+Y(v).toFixed(1);if(i<=S.now)a+=(a?" ":"")+pt;if(i>=S.now)b+=(b?" ":"")+pt;});
      svg.appendChild(el("polyline",{points:a,fill:"none",stroke:color,"stroke-width":w,"stroke-linejoin":"round"}));svg.appendChild(el("polyline",{points:b,fill:"none",stroke:color,"stroke-width":w,"stroke-dasharray":"5 4",opacity:.75}));}
    line(S.ers.map(function(v,i){return i>S.now?null:v;}).filter(function(v){return v!=null;}).concat([]),li,1.6);
    line(S.f27,am,2);line(S.f11,cy,2.4);
    // pit stops
    S.pits.forEach(function(p){svg.appendChild(el("line",{x1:X(p.l),x2:X(p.l),y1:P.t,y2:P.t+ih,stroke:ne,"stroke-dasharray":"3 3"}));
      svg.appendChild(el("text",{x:X(p.l),y:P.t-10,"text-anchor":"middle","font-size":narrow?9.5:10,"font-weight":800,fill:ne,class:"ax-pit-label"},narrow?"BOX L"+p.l:p.t));});
    // now marker + values
    svg.appendChild(el("line",{x1:X(S.now),x2:X(S.now),y1:P.t-6,y2:P.t+ih,stroke:ink,"stroke-width":1.2}));
    svg.appendChild(el("text",{x:X(S.now),y:P.t-10,"text-anchor":"middle","font-size":10,"font-weight":800,fill:ink},"NOW · L"+S.now));
    [[S.f11[S.now],cy,"#11 "+S.f11[S.now]+"%"],[S.f27[S.now],am,"#27 "+S.f27[S.now]+"%"],[S.ers[S.now],li,"ERS "+S.ers[S.now]+"%"]].forEach(function(q){svg.appendChild(el("circle",{cx:X(S.now),cy:Y(q[0]),r:3.5,fill:q[1]}));});
    var fin=S.f11[S.L];svg.appendChild(el("text",{x:W-P.r-2,y:Y(fin)+18,"text-anchor":"end","font-size":10,"font-weight":800,fill:cy},"flag ≈ "+fin+"%"));
    // legend
    var lg=document.createElement("div");lg.className="ax-energy-legend";
    lg.innerHTML=[["#11 fuel",cy,"solid"],["#27 fuel",am,"solid"],["#11 ERS charge",li,"solid"],["projection",mut,"dashed"],["pit stop",ne,"dashed"]].map(function(x){return '<span><i style="border-top:3px '+x[2]+' '+x[1]+'"></i>'+x[0]+'</span>';}).join("")+'<span class="v">Now: #11 '+S.f11[S.now]+'% · #27 '+S.f27[S.now]+'% · ERS '+S.ers[S.now]+'%</span>';
    host.innerHTML="";host.appendChild(svg);host.appendChild(lg);
  }
  var mount=window.ApexCharts.mount;window.ApexCharts.mount=function(){mount();energy();};
  var rt;function redraw(){window.ApexCharts.mount();}window.addEventListener("resize",function(){clearTimeout(rt);rt=setTimeout(redraw,120);});
  document.documentElement.addEventListener("ax:theme",redraw);
})();
