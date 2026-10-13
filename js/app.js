/* Apex Pitwall app shell — Mr Deedz. All clicks wired. */
(function(){
  const D = window.AX_DATA || {kpis:{},drivers:[],radios:[],alerts:[],tyres:[],stints:[]};
  const AX = window.Apex = {
    toast(msg){
      let host=document.querySelector(".toast-host");
      if(!host){ host=document.createElement("div"); host.className="toast-host"; document.body.appendChild(host); }
      const t=document.createElement("div"); t.className="toast"; t.textContent=msg; host.appendChild(t); while(host.children.length>3) host.firstChild.remove();
      setTimeout(()=>t.remove(),3200);
    },
    openDriver(d){
      const el=document.getElementById("axDriverDrawer");
      const bd=document.getElementById("axDrawerBackdrop");
      if(!el){ AX.toast("#"+d.num+" "+d.name+" · "+d.status+" · "+d.tyre); return; }
      el.querySelector("[data-f=num]").textContent="#"+d.num;
      el.querySelector("[data-f=name]").textContent=d.name;
      el.querySelector("[data-f=team]").textContent=d.team;
      el.querySelector("[data-f=status]").textContent=d.status;
      el.querySelector("[data-f=tyre]").textContent=d.tyre;
      el.querySelector("[data-f=gap]").textContent=d.gap;
      el.querySelector("[data-f=fuel]").textContent=d.fuel_pct+"%";
      el.querySelector("[data-f=ers]").textContent=d.ers+"%";
      el.querySelector("[data-f=wear]").textContent=d.wear+"%";
      el.classList.add("open"); if(bd) bd.classList.add("open");
    },
    closeDrawer(){
      document.getElementById("axDriverDrawer")?.classList.remove("open");
      document.getElementById("axDrawerBackdrop")?.classList.remove("open");
    }
  };

  // bind once per element: page init runs again after every in-app swap, chrome elements keep their single listener
  function on(el,ev,fn){ const k="__ax_"+ev; if(!el||el[k]) return; el[k]=1; el.addEventListener(ev,fn); }

  function authGate(){
    const page=(location.pathname.split("/").pop()||"");
    if(page==="login.html"||page==="index.html"||page==="404.html") return;
    if(sessionStorage.getItem("ax_auth")!=="1") location.href="login.html";
  }

  function bindLogin(){
    const form=document.getElementById("loginForm");
    if(!form) return;
    form.addEventListener("submit",(e)=>{
      e.preventDefault();
      const email=form.email.value.trim();
      const pass=form.password.value;
      const err=document.getElementById("loginErr");
      if(email==="ops@apex.demo" && pass==="demo"){
        sessionStorage.setItem("ax_auth","1");
        location.href="pitwall-bridge.html";
      } else if(err){ err.style.display="block"; err.textContent="Use ops@apex.demo / demo"; }
    });
  }

  function theme(){
    const btn=document.getElementById("themeBtn");
    const saved=localStorage.getItem("ax_theme");
    if(saved==="day") document.documentElement.setAttribute("data-theme","day");
    btn?.addEventListener("click",()=>{
      const cur=document.documentElement.getAttribute("data-theme")==="day"?"night":"day";
      if(cur==="day") document.documentElement.setAttribute("data-theme","day");
      else document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("ax_theme", cur);
      AX.toast("Theme · "+cur); document.documentElement.dispatchEvent(new Event("ax:theme"));
    });
  }

  function moreSheet(){
    const btn=document.getElementById("axMoreBtn");
    const sheet=document.getElementById("axMoreSheet");
    btn?.addEventListener("click",()=> sheet?.classList.toggle("open"));
    document.addEventListener("click",(e)=>{
      if(!sheet||!sheet.classList.contains("open")) return;
      if(e.target.closest("#axMoreBtn")||e.target.closest("#axMoreSheet")) return;
      sheet.classList.remove("open");
    });
  }

  function towerClicks(){
    document.querySelectorAll(".ax-lap-cell").forEach(cell=>{
      on(cell,"click",()=>{
        document.querySelectorAll(".ax-lap-cell").forEach(x=>x.classList.remove("active"));
        cell.classList.add("active");
        const code=cell.getAttribute("data-code");
        const d=(D.drivers||[]).find(x=>x.code===code);
        if(d) AX.openDriver(d);
        else AX.toast("Timing · "+(cell.querySelector(".name")?.textContent||code));
      });
    });
  }

  function driverStack(){
    document.querySelectorAll(".ax-driver-card[data-driver]").forEach(card=>{
      on(card,"click",(e)=>{
        // allow real navigation on detail links; cards without href open drawer
        if(card.tagName==="A" && card.getAttribute("href") && !card.getAttribute("href").startsWith("#")) return;
        e.preventDefault();
        document.querySelectorAll(".ax-driver-card").forEach(x=>x.classList.remove("active"));
        card.classList.add("active");
        const id=card.getAttribute("data-driver");
        const d=(D.drivers||[]).find(x=>x.id===id||x.code===id);
        if(d) AX.openDriver(d);
      });
    });
  }

  function trackTools(){
    document.querySelectorAll("[data-track-filter]").forEach(b=>{
      on(b,"click",()=>{
        document.querySelectorAll("[data-track-filter]").forEach(x=>x.classList.remove("active"));
        b.classList.add("active");
        window._axTrack?.setFilter(b.getAttribute("data-track-filter"));
        AX.toast("Track filter · "+b.textContent.trim());
      });
    });
  }

  function actions(){
    document.querySelectorAll("[data-action]").forEach(el=>{
      on(el,"click",(e)=>{
        const act=el.getAttribute("data-action");
        if(el.tagName==="A" && el.getAttribute("href") && el.getAttribute("href")!=="#") return;
        e.preventDefault();
        AX.toast(act+" · queued on pitwall");
      });
    });
    on(document.getElementById("axDrawerClose"),"click", AX.closeDrawer);
    on(document.getElementById("axDrawerBackdrop"),"click", AX.closeDrawer);
  }

  function filters(){
    document.querySelectorAll("[data-filter-table]").forEach(inp=>{
      on(inp,"input",()=>{
        const q=inp.value.toLowerCase();
        const table=document.querySelector(inp.getAttribute("data-filter-table"));
        if(!table) return;
        table.querySelectorAll("tbody tr").forEach(tr=>{
          tr.style.display = tr.textContent.toLowerCase().includes(q) ? "" : "none";
        });
      });
    });
  }


  function settingsPersist(){
    document.querySelectorAll("[data-setting]").forEach(el=>{
      const k="ax_set_"+el.getAttribute("data-setting");
      const saved=localStorage.getItem(k);
      if(saved!=null && "value" in el) el.value=saved;
      on(el,"change",()=>{
        localStorage.setItem(k, el.value);
        if(el.getAttribute("data-setting")==="theme"){
          const day=el.value==="day";
          if(day) document.documentElement.setAttribute("data-theme","day");
          else document.documentElement.removeAttribute("data-theme");
          localStorage.setItem("ax_theme", day?"day":"night");
        }
      });
    });
    const themeSaved=localStorage.getItem("ax_set_theme");
    if(themeSaved==="day"){
      document.documentElement.setAttribute("data-theme","day");
      localStorage.setItem("ax_theme","day");
    } else if(themeSaved==="night"){
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("ax_theme","night");
    }
    document.querySelectorAll('[data-action="Save settings"]').forEach(btn=>{
      on(btn,"click",()=>{
        document.querySelectorAll("[data-setting]").forEach(el=>{
          const k="ax_set_"+el.getAttribute("data-setting");
          localStorage.setItem(k, el.value);
          if(el.getAttribute("data-setting")==="theme"){
            const day=el.value==="day";
            if(day) document.documentElement.setAttribute("data-theme","day");
            else document.documentElement.removeAttribute("data-theme");
            localStorage.setItem("ax_theme", day?"day":"night");
          }
        });
      });
    });
  }

  function mountTrack(){
    const c=document.getElementById("trackCanvas");
    if(window._axTrack && window._axTrack.canvas!==c){ window._axTrack.destroy(); window._axTrack=null; }
    if(c && window.ApexTrack && !window._axTrack) window._axTrack = new ApexTrack(c);
  }
  function stintHistory(){
    const tb=document.getElementById("axStintHist"); if(!tb||!D.stints) return;
    const code=tb.dataset.driver||"VEX";
    tb.innerHTML=D.stints.filter(s=>s.driver===code).map(s=>'<tr><td><a class="mono" href="stint-detail.html">'+s.id+'</a></td><td><span class="badge '+s.compound+'">'+s.compound+'</span></td><td>'+s.laps+'</td><td>'+s.avg+'</td><td>'+s.best+'</td><td>'+s.wear+'%</td><td><span class="badge '+s.status+'">'+s.status+'</span></td></tr>').join("");
  }
  function initPage(){ stintHistory(); trackTools(); settingsPersist(); actions(); filters(); mountTrack(); window.ApexCharts?.mount(); }
  AX.initPage = initPage;

  document.addEventListener("DOMContentLoaded",()=>{
    authGate(); bindLogin(); theme(); moreSheet(); towerClicks(); driverStack();
    initPage(); window.ApexSPA?.init();
  });
})();
