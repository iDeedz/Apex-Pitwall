#!/usr/bin/env python3
"""Single source of truth for race data.

The lap tape (AX_EXTRA.laps: every driver, laps 1..driver.laps, with compound, stint and pit flags)
is generated here from a small set of inputs (driver order/status/tyre/wear/stint, each car's plan,
the timing-tower last laps and the race-best holder). Everything else is DERIVED from that tape:

  * stints (count = driver.stint, laps sum = laps completed, compounds follow the plan order,
    best/avg from the stint's own laps, active wear = driver wear) + the queued next stint for planned cars
  * mounted tyre set age = active stint laps
  * race best lap + holder (fastest lap in the tape, a dry-tyre lap)
  * purple sectors (min of every sector in the tape)
  * count cards and report-index row counts (= rows of the data they describe)

Then every baked (static HTML) copy is regenerated: lap tables, stint tables, ticker, bridge stint
cards, stint-detail, driver stint history, sector-map, count cards. Run it after editing js/data.js inputs:

    python3 tools/derive.py && python3 qa/audit.py
"""
import json, re, glob, random
from pathlib import Path
R = Path(__file__).resolve().parent.parent
def load(p):
    s = (R / p).read_text(); i = s.index('{'); j = s.rindex('}'); return s[:i], json.loads(s[i:j + 1]), s[j + 1:], ('\n' in s[i:j])
pD, D, qD, nlD = load('js/data.js'); pE, E, qE, nlE = load('js/data-extra.js')
sec = lambda s: int(s.split(':')[0]) * 60 + float(s.split(':')[1])
fmt = lambda t: '%d:%06.3f' % (int(t // 60), t - 60 * int(t // 60))
K = D['kpis']; NOW = K['lap']; TOTAL = K['total_laps']
drivers = sorted(D['drivers'], key=lambda d: d['pos'])
tower = {t['code']: t for t in D['tower']}
plans = {int(p['car'][1:]): p for p in D['strategy']}
# implicit plans for cars without a strategy card (current stint compound = current tyre)
IMPLICIT = {'ORB': 'S-M', 'HEX': 'M-H', 'DRK': 'S-I', 'PUL': 'H-M', 'ARC': 'M-H'}
LETTER = {'S': 'SOFT', 'M': 'MEDIUM', 'H': 'HARD', 'I': 'INTER', 'W': 'WET'}
RATE = {'SOFT': 5.5, 'MEDIUM': 3.5, 'HARD': 2.4, 'INTER': 4.5, 'WET': 4.0}          # wear % per lap
OFF = {'SOFT': -0.6, 'MEDIUM': 0.0, 'HARD': 0.5, 'INTER': 2.6, 'WET': 4.0}           # pace offset (dry track)
DEG = {'SOFT': 0.08, 'MEDIUM': 0.05, 'HARD': 0.03, 'INTER': 0.09, 'WET': 0.1}        # s per lap of tyre age
FIXED = {'VEX': [14, 13]}                     # VEX boxes on L14 and L27 (energy timeline, radio)
BEST_BY, BEST_T = K['best_lap_by'], sec(K['best_lap'])
IN_LAP, OUT_LAP = 3.0, round(K['pit_loss'] - 3.0, 1)
rnd = random.Random(1138)

# ================= physical models (per-driver live values) =================
# Snapshot timing: the leader has just completed lap NOW. A car whose gap is larger than the
# snapshot offset (cars within it have already crossed the line) has completed NOW-1 laps.
# Nobody is a lap down (every gap < one lap), so laps completed is NOW or NOW-1, never less.
gsec = lambda g: 0.0 if not g.startswith('+') else float(g[1:])
on_now = [gsec(d['gap']) for d in drivers if d['laps'] == NOW]
TAU = (max(on_now) + min(gsec(d['gap']) for d in drivers if gsec(d['gap']) > max(on_now))) / 2
for d in drivers:
    assert gsec(d['gap']) < 84.0, d['code']
    d['laps'] = NOW if gsec(d['gap']) <= TAU else NOW - 1
# Fuel model: every car starts at 100 %; burn per lap = BASE_BURN x mixture factor of that car.
BASE_BURN = 53 / 38                                     # VEX: 100 % -> 47 % over 38 laps (energy timeline)
MIX = {'VEX': 1.0, 'NOX': 0.962, 'RIN': 1.057, 'SOL': 0.814, 'KAI': 1.0, 'ORB': 0.93, 'HEX': 0.775, 'DRK': 1.143, 'PUL': 0.969, 'ARC': 0.872}
FUEL = lambda d: round(100 - d['laps'] * BASE_BURN * MIX[d['code']])
# ERS state of charge: battery deploy/harvest mode at the snapshot (attack modes drain, harvest refills).
ERS_SOC = {'VEX': 82, 'NOX': 71, 'RIN': 65, 'SOL': 90, 'KAI': 62, 'ORB': 55, 'HEX': 40, 'DRK': 33, 'PUL': 60, 'ARC': 48}
OLD_FER = {d['code']: (d['fuel_pct'], d['ers'], d['wear']) for d in drivers}
for d in drivers:
    d['fuel_pct'] = FUEL(d); d['ers'] = ERS_SOC[d['code']]

def seq_for(d):
    p = plans.get(d['num']); s = (p['compounds'] if p else IMPLICIT[d['code']]).split('-')
    s = [LETTER[c] for c in s]
    assert s[d['stint'] - 1] == d['tyre'], (d['code'], s, d['tyre'])
    return s

laps, stints = [], []
for d in drivers:
    seq = seq_for(d); n = d['stint']; L = d['laps']
    act = max(2, round(d['wear'] / RATE[d['tyre']]))
    if d['code'] in FIXED: lens = FIXED[d['code']] + [L - sum(FIXED[d['code']])]
    else:
        rest = L - act
        lens = [rest] if n == 2 else [rest - rest // 2, rest // 2]
        lens = lens + [act]
    assert len(lens) == n and sum(lens) == L and min(lens) > 0, (d['code'], lens)
    base = 85.2 + 0.11 * (d['pos'] - 1)
    lap = 0
    for si, ln in enumerate(lens):
        comp = seq[si]
        for k in range(ln):
            lap += 1
            t = base + OFF[comp] + DEG[comp] * k - 0.035 * lap + rnd.gauss(0, 0.22)
            pit = None
            if lap == 1: t += 2.2
            if k == ln - 1 and si < n - 1: pit = 'in'; t += IN_LAP
            if k == 0 and si > 0: pit = 'out'; t += OUT_LAP
            if pit is None: t = max(t, BEST_T + 0.08 + rnd.random() * 0.05)
            laps.append({'lap': lap, 'driver': d['code'], 't': round(t, 3), 'compound': comp, 'stint': si + 1, 'pit': pit,
                         'speed_trap': int(318 + rnd.randint(-9, 9) - (8 if comp in ('INTER', 'WET') else 0)), 'ers': rnd.randint(20, 96)})
dvl = {d['code']: d['laps'] for d in drivers}
# race best: the holder's fastest flying lap on a dry compound becomes exactly the race best
cand = [l for l in laps if l['driver'] == BEST_BY and l['pit'] is None and 1 < l['lap'] < dvl[BEST_BY] and l['compound'] in ('SOFT', 'MEDIUM', 'HARD')]
min(cand, key=lambda l: l['t'])['t'] = round(BEST_T, 3)
# last lap of every tower driver = tower last (with tower sectors); live ERS/trap for VEX
last = {}
for l in laps: last[l['driver']] = l
for code, tw in tower.items():
    l = last[code]; l['t'] = round(sec(tw['last']), 3); l['s1'], l['s2'], l['s3'] = tw['s1'], tw['s2'], tw['s3']
dv = {d['code']: d for d in drivers}
for code, l in last.items(): l['ers'] = dv[code]['ers']
last['VEX']['speed_trap'] = 307
# ---- running order from cumulative race time ----
# Timing-line gap: a car with L laps completed is compared with the leader at the same line,
# gap = cum_car(L) - cum_leader(L). Free laps (not pit in/out, not the tower last lap, not the
# race-best lap) absorb the difference evenly so every car's cumulative time lands exactly on its gap.
BEST_LAP = min(cand, key=lambda l: l['t'])
by = {}
for l in laps: by.setdefault(l['driver'], []).append(l)
for v in by.values(): v.sort(key=lambda l: l['lap'])
cum = lambda code, L: sum(l['t'] for l in by[code][:L])
LEAD = drivers[0]['code']
for d in drivers[1:]:
    L = d['laps']; target = round(cum(LEAD, L) + gsec(d['gap']), 3)
    free = [l for l in by[d['code']][:L] if l['pit'] is None and l is not last[d['code']] and l is not BEST_LAP and l['lap'] > 1]
    diff = target - cum(d['code'], L); step = round(diff / len(free), 3)
    for l in free: l['t'] = round(l['t'] + step, 3)
    free[len(free) // 2]['t'] = round(free[len(free) // 2]['t'] + target - cum(d['code'], L), 3)
    assert abs(cum(d['code'], L) - target) < 0.0005, d['code']
    assert min(l['t'] for l in free) > BEST_T, d['code']
GAPS = {d['code']: round(cum(d['code'], d['laps']) - cum(LEAD, d['laps']), 3) for d in drivers}
# sectors for every other lap (sum exactly to the lap time)
for l in laps:
    if 's1' in l: continue
    a = round(l['t'] * (0.336 + rnd.uniform(-0.004, 0.004)), 3); b = round(l['t'] * (0.394 + rnd.uniform(-0.004, 0.004)), 3)
    l['s1'], l['s2'], l['s3'] = a, b, round(l['t'] - a - b, 3)
# order: by lap, then running order
order = {d['code']: d['pos'] for d in drivers}
laps.sort(key=lambda l: (l['lap'], order[l['driver']]))
_m=min(laps,key=lambda l:l['t']); assert _m['t'] == round(BEST_T, 3), _m
E['laps'] = [{k: l[k] for k in ('lap', 'driver', 't', 's1', 's2', 's3', 'compound', 'stint', 'pit', 'speed_trap', 'ers')} for l in laps]

# ---- derived stints ----
sid = 0
for d in drivers:
    my = [l for l in E['laps'] if l['driver'] == d['code']]
    for si in range(1, d['stint'] + 1):
        sl = [l for l in my if l['stint'] == si]; ts = [l['t'] for l in sl]
        comp = sl[0]['compound']; active = si == d['stint']
        sid += 1
        stints.append({'id': 'ST-%03d' % sid, 'driver': d['code'], 'compound': comp, 'laps': len(sl), 'from': sl[0]['lap'], 'to': sl[-1]['lap'],
                       'avg': fmt(sum(ts) / len(ts)), 'best': fmt(min(ts)),
                       'wear': d['wear'] if active else min(95, round(len(sl) * RATE[comp])), 'status': 'Active' if active else 'Complete'})
    seq = seq_for(d)
    if d['code'] in [dd['code'] for dd in drivers if dd['num'] in plans] and len(seq) > d['stint']:
        p = plans[d['num']]; m = re.search(r'L(\d+)', p['win']); box = int(m.group(1)) if m else NOW
        sid += 1
        stints.append({'id': 'ST-%03d' % sid, 'driver': d['code'], 'compound': seq[d['stint']], 'laps': TOTAL - box, 'from': box + 1, 'to': TOTAL,
                       'avg': '—', 'best': '—', 'wear': 0, 'status': 'Queued'})
D['stints'] = stints
# ---- mounted set age = active stint laps ----
act = {s['driver']: s for s in stints if s['status'] == 'Active'}
for t in D['tyres']:
    if t['status'] == 'Mounted':
        code = next(dd['code'] for dd in drivers if dd['num'] == int(t['car'][4:]))
        t['age'] = act[code]['laps']; assert t['compound'] == act[code]['compound']
# Tyre thermal model: heat and pressure follow where the set is (deterministic per set id).
AIR = K['air_temp']
HOTR = {'SOFT': (104, 110), 'MEDIUM': (98, 104), 'HARD': (92, 98), 'INTER': (86, 92), 'WET': (80, 86)}
def tyre_state(t):
    u = (int(t['id'][4:]) * 37 % 100) / 100.0
    st = t['status']
    if st == 'Mounted': lo, hi = HOTR[t['compound']]; heat = round(lo + (hi - lo) * u); press = round(22.6 + 1.8 * u, 1)
    elif st == 'Blanket': heat = round(70 + 10 * u); press = round(21.0 + 1.4 * u, 1)
    elif st == 'Scrubbed': heat = round(48 + 22 * u); press = round(20.8 + 1.4 * u, 1)
    else: heat = round(AIR + 1 + 6 * u); press = round(19.6 + 1.2 * u, 1)        # Cage / Retired: ambient
    t['heat'], t['press'] = heat, press
for t in D['tyres']:
    tyre_state(t)
    if t['status'] in ('Scrubbed', 'Retired') and t['age'] == 0: t['age'] = 1   # a scrubbed/retired set has run
PSTATE = lambda h: 'Hot' if h >= 90 else 'Warm' if h >= 60 else 'Cold'
K['tyres_ready'] = sum(1 for t in D['tyres'] if t['status'] in ('Cage', 'Blanket'))
# ---- race session best + purple sectors ----
for s in D['sessions']:
    if s['id'] == 'SES-RACE': s['best'] = K['best_lap']; s['laps'] = NOW
PURPLE = {k: min(E['laps'], key=lambda l: l[k]) for k in ('s1', 's2', 's3')}
# ---- pit status must agree with the plan: a car may only show PIT if its plan has a stop left ----
def plan_seq(d):
    p = plans.get(d['num']); return (p['compounds'] if p else IMPLICIT[d['code']]).split('-')
for d in drivers:
    if d['status'] == 'PIT' and d['stint'] >= len(plan_seq(d)):
        d['status'] = 'LIVE'
        if d['delta'] == 'BOX': d['delta'] = '+0.164'
for c in D['cars']:
    dd = next((x for x in drivers if x['name'] == c['driver']), None)
    if dd: c['status'] = dd['status']

def save(p, pre, obj, post, nl): (R / p).write_text(pre + json.dumps(obj, indent=2 if nl else None, ensure_ascii=False) + post)
save('js/data.js', pD, D, qD, nlD); save('js/data-extra.js', pE, E, qE, nlE)

# ================= baked copies =================
S = {s['id']: s for s in stints}
def lrow(l): return f'<tr><td>{l["lap"]}</td><td>{l["driver"]}</td><td>{fmt(l["t"])}</td><td>{l["s1"]:.3f}</td><td>{l["s2"]:.3f}</td><td>{l["s3"]:.3f}</td><td>{l["speed_trap"]} km/h</td><td>{l["ers"]}%</td></tr>'
def srow(x, drv=True): return (f'<tr><td><a class="mono" href="stint-detail.html">{x["id"]}</a></td>' + (f'<td>{x["driver"]}</td>' if drv else '') +
    f'<td><span class="badge {x["compound"]}">{x["compound"]}</span></td><td>{x["laps"]}</td><td>{x["avg"]}</td><td>{x["best"]}</td><td>{x["wear"]}%</td><td><span class="badge {x["status"]}">{x["status"]}</span></td></tr>')
def stick(x): return f'<span class="{x["compound"]}">[{x["id"]}] {x["driver"]} · {x["compound"]} · {x["laps"]} laps · wear {x["wear"]}% · {x["status"]}</span>'
def scard(x): return f'<div class="card-item"><div><strong>{x["id"]} · {x["driver"]}</strong><div class="meta">{x["compound"]} · {x["laps"]} laps · best {x["best"]}</div></div><span class="badge {x["status"]}">{x["status"]}</span></div>'
LAPHD = '<th>Lap</th><th>Driver</th><th>Time</th><th>S1</th><th>S2</th><th>S3</th><th>Trap</th><th>ERS</th>'
STHD = '<th>ID</th><th>Driver</th><th>Compound</th><th>Laps</th><th>Avg</th><th>Best</th><th>Wear</th><th>Status</th>'
counts = {'Stints': len(stints), 'Laps taped': len(E['laps'])}
REPORT_ROWS = {'Lap tape': len(E['laps']), 'ST-*': len(stints), 'TYR-*': len(D['tyres']), 'INC-*': len(D['incidents']), 'GST-*': len(D['guests']),
               'RAD-*': len(D['radios']), 'PRT-*': len(D['parts']), 'ALR-*': len(D['alerts'])}
REPORT_ROWS.update({s['name']: s['laps'] for s in D['sessions']})
def tbody_sub(h, head, build):
    out, pos = [], 0
    for m in re.finditer(r'<thead><tr>' + re.escape(head) + r'</tr></thead><tbody>(.*?)</tbody>', h, re.S):
        rows = re.findall(r'<tr>.*?</tr>', m.group(1)); out.append(h[pos:m.start(1)] + build(rows)); pos = m.end(1)
    return ''.join(out) + h[pos:]
def laps_build(rows):
    first = [re.match(r'<tr><td>(\d+)</td><td>([A-Z]{3})</td>', r) for r in rows]; first = [f for f in first if f]
    n = len(rows); drv = {f.group(2) for f in first}; start = int(first[0].group(1)) if first else 1
    pool = [l for l in E['laps'] if (len(drv) > 1 or l['driver'] in drv) and l['lap'] >= start]
    return ''.join(lrow(l) for l in pool[:n])
def stints_build(rows): return ''.join(srow(x) for x in stints[:max(len(rows), len(stints))])
for f in sorted(glob.glob(str(R / '*.html'))):
    h = open(f).read(); o = h; name = Path(f).name
    h = tbody_sub(h, LAPHD, laps_build)
    h = tbody_sub(h, STHD, stints_build)
    # ticker: replace the contiguous run of stint spans
    h = re.sub(r'<span class="[A-Z]+">\[ST-\d{3}\][^<]*</span>(?:   ✦   <span class="[A-Z]+">\[ST-\d{3}\][^<]*</span>)*', lambda m: '   ✦   '.join(stick(x) for x in stints), h)
    # bridge stint cards
    h = re.sub(r'(<h2>Active / recent stints</h2>)(?:<div class="card-item"><div><strong>ST-\d{3}.*?</span></div>)+', lambda m: m.group(1) + ''.join(scard(x) for x in stints[:8]), h)
    # driver stint history (static fallback of the runtime renderer)
    h = re.sub(r'(<tbody id="axStintHist" data-driver="(\w+)">).*?(</tbody>)', lambda m: m.group(1) + ''.join(srow(x, False) for x in stints if x['driver'] == m.group(2)) + m.group(3), h, flags=re.S)
    # count cards
    for lab, v in counts.items():
        h = re.sub(r'(<div class="label">' + lab + r'</div><div class="value[^"]*"[^>]*>)\d+(</div>)', r'\g<1>%d\2' % v, h)
    h = re.sub(r'the other \d+ logged stints', 'the other %d logged stints' % (len(stints) - 1), h)
    if name == 'reports.html':
        def rr(m): return m.group(1) + str(REPORT_ROWS.get(m.group(2), int(m.group(3)))) + m.group(4)
        h = re.sub(r'(<tr><td>[^<]+</td><td>([^<]+)</td><td>)(\d+)(</td>)', rr, h)
        nrows = len(re.findall(r'<tr>', h[h.find('<h2>Report index'):h.find('</tbody>', h.find('<h2>Report index'))])) - 1
        h = re.sub(r'(<div class="label">Packs</div><div class="value[^"]*"[^>]*>)\d+(</div>)', r'\g<1>%d\2' % nrows, h)
    if name == 'sector-map.html':
        for i, (k, cls) in enumerate((('s1', 'purple'), ('s2', 'green'), ('s3', 'yellow'))):
            p = PURPLE[k]
            h = re.sub(r'(<div class="s">SECTOR %d</div><div class="t">)[\d.]+(</div><div class="meta">)[^<]+' % (i + 1), r'\g<1>%.3f\2Purple · %s L%d' % (p[k], p['driver'], p['lap']), h)
    if name == 'stint-detail.html':
        x = stints[0]; avg = x['avg']; best = x['best']; spread = '+%.3fs' % (sec(avg) - sec(best)) if best != '—' else '—'
        h = re.sub(r'<h1>Stint detail · ST-\d+</h1><p>[^<]*</p>', f'<h1>Stint detail · {x["id"]}</h1><p>{x["driver"]} · {x["compound"]} · {x["laps"]} laps · L{x["from"]}–L{x["to"]}</p>', h)
        for lab, v in (('Avg', avg), ('Best', best), ('Wear', '%d%%' % x['wear']), ('Status', x['status'])):
            h = re.sub(r'(<div class="label">%s</div><div class="value">)[^<]*(</div>)' % lab, r'\g<1>%s\2' % v, h, count=1)
        for lab, v, meta in (('Stint', x['id'], x['driver']), ('Compound', x['compound'], 'Stint %d' % ([s['id'] for s in D['stints'] if s['driver']==x['driver']].index(x['id'])+1)), ('Laps', str(x['laps']), 'L%d–L%d' % (x['from'], x['to'])), ('Spread', spread, 'Avg − best')):
            h = re.sub(r'(<div class="label">%s</div><div class="value text-sm" style="font-size:1.05rem">)[^<]*(</div><div class="meta">)[^<]*' % lab, r'\g<1>%s\g<2>%s' % (v, meta), h, count=1)
        h = re.sub(r'<p>[^<]*Compare against the other \d+ logged stints[^<]*</p>', f'<p>{x["status"]} {x["compound"].lower()} for {x["driver"]}, laps {x["from"]}–{x["to"]}. Compare against the other {len(stints) - 1} logged stints before calling the undercut — every figure here is derived from the lap tape.</p>', h)
    # driver pit status (rail cards, driver tables, field card)
    for d in drivers:
        st = d['status']
        h = re.sub(r'(<strong>%s</strong><span>)[A-Z]+ · [A-Z]+(</span></div><div class="delta )[a-z]+(">)[^<]*' % d['code'],
                   lambda m: m.group(1) + '%s · %s' % (d['tyre'], st) + m.group(2) + ('pit' if st == 'PIT' else 'ahead' if d['delta'].startswith('-') else 'leader' if d['pos'] == 1 else 'behind') + m.group(3) + d['delta'], h)
        h = re.sub(r'(<a class="mono" href="driver-detail.html">%s</a></td>(?:<td>[^<]*</td>){3}<td><span class="badge \w+">\w+</span></td><td>[^<]*</td><td>)[^<]*(</td>(?:<td>[^<]*</td>){3}<td><span class="badge )\w+(">)\w+' % d['code'],
                   lambda m: m.group(1) + d['delta'] + m.group(2) + st + m.group(3) + st, h)
    # any table row that names exactly one car: its status badge / BOX gap follow that driver
    def fixrow(m):
        r = m.group(0); who = [d for d in drivers if re.search(r'>%s<|>#%d<|%s|CAR-%02d\b' % (d['code'], d['num'], d['name'], d['num']), r)]
        if len(who) != 1: return r
        d = who[0]
        r = re.sub(r'badge (PIT|LIVE)">(PIT|LIVE)', 'badge %s">%s' % (d['status'], d['status']), r)
        if d['status'] != 'PIT': r = r.replace('<td>BOX</td>', '<td>%s</td>' % d['delta'])
        return r
    h = re.sub(r'<tr>(?:(?!</tr>).)*</tr>', fixrow, h, flags=re.S)
    # per-driver Fuel / ERS / Wear cells, located by the table's header names
    def fix_table(m):
        tb = m.group(0); hd = re.findall(r'<th[^>]*>(.*?)</th>', tb.split('</thead>')[0]) if '</thead>' in tb else []
        cols = {k: i for i, x in enumerate(hd) for k in ('Fuel', 'ERS', 'Wear') if re.sub('<[^>]+>', '', x).strip() == k}
        if 'Fuel' not in cols and 'ERS' not in cols: return tb
        if any(re.sub('<[^>]+>', '', x).strip() == 'Lap' for x in hd): return tb   # lap tables carry per-lap ERS from the tape      # e.g. stint tables have their own Wear
        def fr(mm):
            r = mm.group(0); who = [d for d in drivers if re.search(r'>%s<|>#%d<|%s' % (d['code'], d['num'], d['name']), r)]
            if len(who) != 1: return r
            d = who[0]; cells = re.findall(r'<td>(?:(?!</td>).)*</td>', r, re.S)
            if len(cells) != len(hd): return r
            for k, i in cols.items():
                v = {'Fuel': d['fuel_pct'], 'ERS': d['ers'], 'Wear': d['wear']}[k]
                cells[i] = re.sub(r'\d+%', '%d%%' % v, cells[i], count=1)
            pre = r[:r.index('<td>')]; return pre + ''.join(cells) + '</tr>'
        return re.sub(r'<tr>(?:(?!</tr>).)*</tr>', fr, tb, flags=re.S)
    h = re.sub(r'<table class="data">(?:(?!</table>).)*</table>', fix_table, h, flags=re.S)
    npit = sum(1 for d in drivers if d['status'] == 'PIT')
    h = re.sub(r'\d+ live · \d+ pit', ('%d live · %d pit' % (len(drivers) - npit, npit)) if npit else '%d live · none in pit' % len(drivers), h)
    # tyre-set detail cards: derived from AX_DATA.tyres + the lap tape
    if name == 'tire-set-detail.html':
        tid = re.search(r'<h1>Tyre set · (TYR-\d+)</h1>', h).group(1); t = next(x for x in D['tyres'] if x['id'] == tid)
        dd = next(x for x in drivers if x['num'] == int(t['car'][4:]))
        if t['status'] == 'Mounted':
            a_ = act[dd['code']]; fit = 'Fitted L%d' % a_['from']; hist = 'L%d–L%d' % (a_['from'], a_['to']); hm = 'On car · %s' % dd['status'].lower()
        else:
            fit = t['status']; hist = 'Logged'; hm = t['status']
        for lab, v, meta in (('Heat', '%dC' % t['heat'], hm), ('Press', '%.1f psi' % t['press'], PSTATE(t['heat'])), ('Age', '%d laps' % t['age'], hist), ('Status', t['status'], fit)):
            h = re.sub(r'(<div class="label">%s</div><div class="value">)[^<]*(</div><div class="meta">)([^<]*)' % lab, lambda m: m.group(1) + v + m.group(2) + (meta if meta is not None else m.group(3)), h, count=1)
        for lab, v, meta in (('Set', t['id'], t['set']), ('Compound', t['compound'], ('Fresh ' if t['age'] <= 3 else 'Used ') + t['compound'].lower()), ('Driver', dd['code'], '#%d · %s' % (dd['num'], dd['team'])), ('Car', t['car'], dd['status'])):
            h = re.sub(r'(<div class="label">%s</div><div class="value text-sm" style="font-size:1.05rem">)[^<]*(</div><div class="meta">)[^<]*' % lab, lambda m: m.group(1) + v + m.group(2) + meta, h, count=1)
        h = re.sub(r'<p>[A-Z0-9]+ · [A-Z]+ · CAR-\d+</p>', '<p>%s · %s · %s</p>' % (t['set'], t['compound'], t['car']), h, count=1)
        h = re.sub(r'(<div class="label">Car</div>.*?<div class="meta">[^<]*</div></div>)', lambda m: m.group(1), h, count=1)
        h = re.sub(r'(Mounted|Cage|Blanket|Scrubbed|Retired) [a-z]+ on CAR-\d+\.', '%s %s on %s.' % (t['status'], t['compound'].lower(), t['car']), h, count=1)
    # sampled tables are labelled with what they show
    if name == 'driver-coaching.html':
        nrow = len(re.search(r'<div class="ax-panel" id="deskCoach">.*?<tbody>(.*?)</tbody>', h, re.S).group(1).split('<tr>')) - 1
        h = re.sub(r'<h2>Coaching bank[^<]*</h2>', '<h2>Coaching bank · first %d of %d notes</h2>' % (nrow, len(E['notes'])), h)
        h = re.sub(r'(<div class="label">Notes</div><div class="value[^"]*"[^>]*>)\d+(</div><div class="meta">)[^<]*', r'\g<1>%d\g<2>Bank · %d shown below' % (len(E['notes']), nrow), h)
    if name == 'empty.html':
        nrow = len(re.search(r'<h2>[^<]*alert archive[^<]*</h2>.*?<tbody>(.*?)</tbody>', h, re.S | re.I).group(1).split('<tr>')) - 1
        h = re.sub(r'<h2>[^<]*alert archive[^<]*</h2>', '<h2>Alert archive · all %d alerts</h2>' % nrow, h, flags=re.I)
        h = h.replace('<label>Cleared alert archive</label>', '<label>Alert archive</label>')
    if name == 'travel-logistics.html':
        g = len(D['guests']); w = len(D['weekend'])
        h = re.sub(r'(<div class="label">Movements</div><div class="value[^"]*"[^>]*>)\d+(</div><div class="meta">)[^<]*', r'\g<1>%d\g<2>%d guest · %d team' % (g + w, g, w), h)
    if h != o: open(f, 'w').write(h)
print('laps', len(E['laps']), 'stints', len(stints), 'best', K['best_lap'], BEST_BY, 'purple', {k: (v[k], v['driver'], v['lap']) for k, v in PURPLE.items()})
