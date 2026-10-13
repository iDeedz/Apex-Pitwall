/* Apex live track / sector canvas */
(function(){
  function ApexTrack(canvas){
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.filter = "all";
    this.cars = (window.AX_DATA && window.AX_DATA.drivers) ? window.AX_DATA.drivers.slice() : [];
    this.t = 0;
    this._resize = this._resize.bind(this);
    this._draw = this._draw.bind(this);
    this._click = this._click.bind(this);
    window.addEventListener("resize", this._resize);
    canvas.addEventListener("click", this._click);
    this._resize();
    this._raf = requestAnimationFrame(this._draw);
  }
  ApexTrack.prototype.setFilter = function(f){ this.filter = f || "all"; };
  ApexTrack.prototype.destroy = function(){ this.dead = true; cancelAnimationFrame(this._raf); window.removeEventListener("resize", this._resize); this.canvas.removeEventListener("click", this._click); };
  ApexTrack.prototype._resize = function(){
    const p = this.canvas.parentElement;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(260, p.clientWidth || 800);
    // phones/tablets: the HUD sits above the canvas, so the canvas owns a fixed height instead of filling the panel
    const h = window.innerWidth <= 600 ? 260 : window.innerWidth <= 900 ? 300 : Math.max(280, p.clientHeight || 420);
    this.canvas.width = Math.floor(w * dpr);
    this.canvas.height = Math.floor(h * dpr);
    this.canvas.style.width = w + "px";
    this.canvas.style.height = h + "px";
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.w = w; this.h = h;
  };
  ApexTrack.prototype._trackPath = function(ctx, w, h){
    const cx = w * 0.5, cy = h * 0.52;
    const rx = Math.min(w, h) * 0.38, ry = Math.min(w, h) * 0.28;
    ctx.beginPath();
    // stylized GP circuit (not oval farm pools)
    ctx.moveTo(cx - rx, cy);
    ctx.bezierCurveTo(cx - rx, cy - ry, cx - rx * 0.2, cy - ry * 1.15, cx + rx * 0.15, cy - ry * 0.85);
    ctx.bezierCurveTo(cx + rx * 0.55, cy - ry * 0.5, cx + rx, cy - ry * 0.6, cx + rx * 0.95, cy);
    ctx.bezierCurveTo(cx + rx * 0.9, cy + ry * 0.7, cx + rx * 0.2, cy + ry * 1.05, cx - rx * 0.25, cy + ry * 0.75);
    ctx.bezierCurveTo(cx - rx * 0.7, cy + ry * 0.45, cx - rx, cy + ry * 0.5, cx - rx, cy);
    ctx.closePath();
  };
  ApexTrack.prototype._posOnTrack = function(pct, w, h){
    // approximate positions along ellipse-ish lap
    const a = pct * Math.PI * 2 - Math.PI * 0.5;
    const cx = w * 0.5, cy = h * 0.52;
    const rx = Math.min(w, h) * 0.38, ry = Math.min(w, h) * 0.28;
    // warp for hairpin feel
    const warp = 1 + 0.08 * Math.sin(a * 3);
    return { x: cx + Math.cos(a) * rx * warp, y: cy + Math.sin(a) * ry };
  };
  ApexTrack.prototype._draw = function(){
    if (this.dead || !this.canvas.isConnected) return;
    this.t += 0.008;
    const ctx = this.ctx, w = this.w, h = this.h;
    ctx.clearRect(0, 0, w, h);
    // asphalt plate
    const g = ctx.createRadialGradient(w*0.5, h*0.4, 20, w*0.5, h*0.5, Math.max(w,h)*0.6);
    g.addColorStop(0, "#1A1218"); g.addColorStop(1, "#08060A");
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
    // runoff
    ctx.save();
    this._trackPath(ctx, w, h);
    ctx.strokeStyle = "rgba(255,45,85,0.15)"; ctx.lineWidth = 36; ctx.stroke();
    ctx.strokeStyle = "#2A2E38"; ctx.lineWidth = 22; ctx.stroke();
    ctx.strokeStyle = "#F4F6FB"; ctx.lineWidth = 2; ctx.setLineDash([10, 8]); ctx.stroke();
    ctx.setLineDash([]);
    // start/finish
    const sf = this._posOnTrack(0, w, h);
    ctx.fillStyle = "#FF2D55";
    ctx.fillRect(sf.x - 6, sf.y - 14, 12, 28);
    ctx.fillStyle = "#fff"; ctx.font = "bold 9px sans-serif";
    ctx.fillText("S/F", sf.x - 8, sf.y - 18);
    ctx.font = "bold 9px sans-serif";
    const labels = [{t: "S/F bar", x: sf.x - 6, y: sf.y - 14, w: 12, h: 28}, {t: "S/F", x: sf.x - 8, y: sf.y - 26, w: ctx.measureText("S/F").width, h: 10}]; this._pitN = 0;
    // sector markers
    [["S1",0.28],["S2",0.58],["S3",0.88]].forEach(([lab,p])=>{
      const pt = this._posOnTrack(p, w, h);
      ctx.fillStyle = "#3DDCFF"; ctx.beginPath(); ctx.arc(pt.x, pt.y, 4, 0, Math.PI*2); ctx.fill();
      // sector labels sit OUTSIDE the racing line (radial offset), car numbers sit INSIDE, so they never meet
      const cx = w * 0.5, cy = h * 0.52, dx = pt.x - cx, dy = pt.y - cy, d = Math.hypot(dx, dy) || 1;
      ctx.font = "bold 10px monospace"; const tw = ctx.measureText(lab).width;
      const lx = pt.x + dx / d * 26 - tw / 2, ly = pt.y + dy / d * 24 + 4;
      ctx.fillStyle = "#8B93A7"; ctx.fillText(lab, lx, ly);
      labels.push({t: lab, x: lx, y: ly - 9, w: tw, h: 11});
    });
    // DRS zones
    ctx.strokeStyle = "rgba(184,255,74,0.45)"; ctx.lineWidth = 3;
    [0.1, 0.7].forEach(p=>{
      const a = this._posOnTrack(p, w, h), b = this._posOnTrack(p+0.06, w, h);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    });
    // cars
    const list = this.cars.filter(c=>{
      if(this.filter === "all") return true;
      if(this.filter === "PIT") return c.status === "PIT";
      if(this.filter === "LIVE") return c.status === "LIVE";
      if(this.filter === "SOFT" || this.filter === "MEDIUM" || this.filter === "HARD") return c.tyre === this.filter;
      return true;
    });
    // pass 1: positions (pit-lane cars park inside start/finish)
    const placed = list.map(car => {
      const base = ((car.pos - 1) * 0.07 + this.t * (car.status === "PIT" ? 0 : 0.15)) % 1;
      let pt = this._posOnTrack(base, w, h);
      if (car.status === "PIT") { const s0 = this._posOnTrack(0, w, h), pi = (this._pitN = (this._pitN || 0) + 1) - 1; pt = { x: s0.x - 14 + pi * 30, y: s0.y + Math.min(44, h * 0.14) }; }
      car._xy = pt; return { car, pt };
    });
    const hit = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
    const obstacles = labels.concat(placed.map(p => ({ x: p.pt.x - 8, y: p.pt.y - 6, w: 16, h: 12 })));
    // pass 2: cars, then each number label at the first free slot (inside, further inside, outside, either side)
    placed.forEach(({ car, pt }) => {
      ctx.save(); ctx.translate(pt.x, pt.y);
      ctx.fillStyle = car.pos === 1 ? "#B8FF4A" : (car.status === "PIT" ? "#FFC107" : "#FF2D55");
      ctx.beginPath(); ctx.moveTo(8, 0); ctx.lineTo(-6, -5); ctx.lineTo(-4, 0); ctx.lineTo(-6, 5); ctx.closePath(); ctx.fill();
      ctx.restore();
    });
    placed.forEach(({ car, pt }) => {
      const cx = w * 0.5, cy = h * 0.52, dx = cx - pt.x, dy = cy - pt.y, d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d;
      const lab = "#" + car.num; ctx.font = "bold 9px monospace"; const tw = ctx.measureText(lab).width;
      const cand = [[ux*20, uy*18], [ux*34, uy*32], [-ux*24, -uy*22], [-uy*26 + ux*8, ux*26 + uy*8], [uy*26 + ux*8, -ux*26 + uy*8], [ux*48, uy*46]];
      let box = null;
      for (const [ox, oy] of cand) { const b = { t: lab, x: pt.x + ox - tw / 2, y: pt.y + oy - 5, w: tw, h: 10 };
        if (b.x < 0 || b.y < 0 || b.x + b.w > w || b.y + b.h > h) continue;
        if (!obstacles.some(o => hit(o, b)) && !labels.some(o => hit(o, b))) { box = b; break; } }
      if (!box) box = { t: lab, x: pt.x + cand[0][0] - tw / 2, y: pt.y + cand[0][1] - 5, w: tw, h: 10 };
      ctx.fillStyle = "#F4F6FB"; ctx.fillText(lab, box.x, box.y + 8); labels.push(box);
    });
    this._hit = list; this._labels = labels;
    this._raf = requestAnimationFrame(this._draw);
  };
  ApexTrack.prototype._click = function(e){
    const r = this.canvas.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    const hit = (this._hit || []).find(c => c._xy && Math.hypot(c._xy.x - x, c._xy.y - y) < 16);
    if(hit && window.Apex) window.Apex.openDriver(hit);
  };
  window.ApexTrack = ApexTrack;
})();
