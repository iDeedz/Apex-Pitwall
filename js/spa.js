/* Apex Pitwall: content-only navigation. Fetches the target page, swaps only <main>, keeps the tower,
 * driver stack, radio rail and ticker in place (their scroll positions survive), pushState + back/forward.
 * On file:// (fetch blocked) or any error it falls back to a normal page load. */
(function () {
  'use strict';
  var seq = 0, SKIP = { 'login.html': 1, 'index.html': 1 };
  function file(href) { return (href.split('#')[0].split('?')[0].split('/').pop()) || 'pitwall-bridge.html'; }
  function closeChrome() {
    var s = document.getElementById('axMoreSheet'); if (s) s.classList.remove('open');
    if (window.Apex && Apex.closeDrawer) Apex.closeDrawer();
  }
  function markActive(f) {
    document.querySelectorAll('.ax-stint-link,.ax-more-link,.ax-mini-nav a').forEach(function (a) {
      var on = file(a.getAttribute('href') || '') === f; a.classList.toggle('active', on);
      if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
  }
  function loader(main, name, my) {
    var box = document.createElement('div'); box.className = 'ax-loader'; box.setAttribute('role', 'status');
    box.innerHTML = '<div class="ax-loader-term"><div class="ln"><span class="pr">pitwall@apex:~$</span> <span class="cmd"></span><span class="cur" aria-hidden="true"></span></div><div class="bar"><i></i></div><div class="sub">GET /' + name + '.html</div></div>';
    main.innerHTML = ''; main.appendChild(box);
    var cmd = 'loading ' + name.replace(/-/g, ' ') + '…', i = 0, el = box.querySelector('.cmd');
    (function type() { if (my !== seq || !el.isConnected) return; el.textContent = cmd.slice(0, ++i); if (i < cmd.length) setTimeout(type, 12); })();
    setTimeout(function () { var b = box.querySelector('.bar i'); if (b) b.style.width = '60%'; }, 20);
    return box;
  }
  function go(href, push) {
    var f = file(href), main = document.querySelector('main.ax-stage');
    if (location.protocol === 'file:' || !main || SKIP[f]) { location.href = href; return; }
    var my = ++seq, t0 = Date.now(), name = f.replace('.html', '');
    closeChrome(); markActive(f);
    if (window._axTrack) { window._axTrack.destroy(); window._axTrack = null; }
    var box = loader(main, name, my);
    if (innerWidth <= 900) window.scrollTo(0, 0); else main.scrollTop = 0;
    fetch(href, { credentials: 'same-origin' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); }).then(function (html) {
      if (my !== seq) return;
      var doc = new DOMParser().parseFromString(html, 'text/html'), nm = doc.querySelector('main.ax-stage');
      if (!nm || !doc.querySelector('.ax-app')) { location.href = href; return; }
      var b = box.querySelector('.bar i'); if (b) b.style.width = '100%'; var sub = box.querySelector('.sub'); if (sub) sub.textContent = 'GET /' + f + ' · 200 OK';
      setTimeout(function () {
        if (my !== seq) return;
        var cur = document.querySelector('main.ax-stage'), fresh = document.importNode(nm, true);
        fresh.classList.add('ax-view-in'); cur.replaceWith(fresh);
        document.title = doc.title;
        if (push) history.pushState({ ax: f }, '', href);
        if (innerWidth <= 900) window.scrollTo(0, 0); else fresh.scrollTop = 0;
        window.Apex.initPage();
        document.dispatchEvent(new CustomEvent('ax:page', { detail: f }));
      }, Math.max(0, 240 - (Date.now() - t0)));
    }).catch(function () { location.href = href; });
  }
  window.ApexSPA = {
    go: go,
    init: function () {
      if (!document.querySelector('main.ax-stage')) return;
      history.replaceState({ ax: file(location.pathname) }, '', location.href);
      markActive(file(location.pathname));
      document.addEventListener('click', function (e) {
        var a = e.target.closest && e.target.closest('a[href]');
        if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target || a.hasAttribute('download')) return;
        var h = a.getAttribute('href');
        if (!/^[\w.-]+\.html(\?[^#]*)?$/.test(h) || SKIP[file(h)]) return;
        e.preventDefault(); go(h, true);
      });
      window.addEventListener('popstate', function () { go(file(location.pathname) + location.search, false); });
    }
  };
})();
