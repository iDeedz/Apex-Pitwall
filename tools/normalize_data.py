#!/usr/bin/env python3
"""One-off number-book normaliser: every lap time = s1+s2+s3, stint best <= avg,
race best lap = the fastest race lap anywhere. Rewrites js/data*.js and the baked HTML."""
import json, re, glob, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
def load(p, var):
    s = (R / p).read_text(); i = s.index('{'); j = s.rindex('}')
    return s[:i], json.loads(s[i:j+1]), s[j+1:]
def save(p, pre, obj, post, indent):
    (R / p).write_text(pre + json.dumps(obj, indent=indent, ensure_ascii=False) + post)
sec = lambda s: int(s.split(':')[0]) * 60 + float(s.split(':')[1])
fmt = lambda t: '%d:%06.3f' % (int(t // 60), t - 60 * int(t // 60))
def rescale(o, total):
    S = o['s1'] + o['s2'] + o['s3']
    a = round(o['s1'] * total / S, 3); b = round(o['s2'] * total / S, 3)
    o['s1'], o['s2'], o['s3'] = a, b, round(total - a - b, 3)
pD, D, qD = load('js/data.js', 'AX_DATA'); pE, E, qE = load('js/data-extra.js', 'AX_EXTRA')
for t in D['tower']: rescale(t, sec(t['last']))
for l in E['laps']: rescale(l, l['t'])
swapped = []
for s in D['stints']:
    if sec(s['best']) > sec(s['avg']): swapped.append((s['id'], s['driver'], s['avg'], s['best'])); s['avg'], s['best'] = s['best'], s['avg']
lap = D['kpis']['lap']
cands = [(sec(t['last']), t['code'], 'tower') for t in D['tower']]
cands += [(l['t'], l['driver'], 'lap %d' % l['lap']) for l in E['laps'] if l['lap'] <= lap]
cands += [(sec(s['best']), s['driver'], s['id']) for s in D['stints']]
best = min(cands); best_str = fmt(best[0]); old_best = D['kpis']['best_lap']
D['kpis']['best_lap'] = best_str; D['kpis']['best_lap_by'] = best[1]
for s in D['sessions']:
    if s['id'] == 'SES-RACE': s['best'] = best_str
# queued stints have no laps yet: they cannot carry a lap faster than the race best
save('js/data.js', pD, D, qD, 2); save('js/data-extra.js', pE, E, qE, None)
lapmap = {(l['lap'], l['driver']): l for l in E['laps']}
rx = re.compile(r'<tr><td>(\d+)</td><td>([A-Z]{3})</td><td>(\d:\d\d\.\d{3})</td><td>[\d.]+</td><td>[\d.]+</td><td>[\d.]+</td>')
def lrow(m):
    l = lapmap[(int(m.group(1)), m.group(2))]; assert fmt(l['t']) == m.group(3), m.group(0)
    return '<tr><td>%s</td><td>%s</td><td>%s</td><td>%.3f</td><td>%.3f</td><td>%.3f</td>' % (m.group(1), m.group(2), m.group(3), l['s1'], l['s2'], l['s3'])
n = {'laps': 0, 'stint': 0, 'best': 0}
for f in glob.glob(str(R / '*.html')):
    h = open(f).read(); o = h
    h, k = rx.subn(lrow, h); n['laps'] += k
    for sid, drv, A, B in swapped:
        h, k = re.subn(r'(%s</a></td><td>%s</td>(?:(?!</tr>).)*?</td><td>\d+</td><td>)%s(</td><td>)%s(</td>)' % (sid, drv, re.escape(A), re.escape(B)), r'\g<1>%s\g<2>%s\g<3>' % (B, A), h); n['stint'] += k
        h, k = re.subn(r'(%s · %s</strong><div class="meta">[^<]*?best )%s' % (sid, drv, re.escape(B)), r'\g<1>%s' % A, h); n['stint'] += k
    # race-best contexts only (KPI card, Race session rows, session headline); never a blind global replace
    for a, b in [('<div class="value">%s</div>', '<div class="value">%s</div>'), ('<td>38</td><td>%s</td><td>Dry', '<td>38</td><td>%s</td><td>Dry'), ('Dry · wind 12kts</td><td>%s</td>', 'Dry · wind 12kts</td><td>%s</td>'), ('38 laps · best %s', '38 laps · best %s')]:
        k = h.count(a % old_best); h = h.replace(a % old_best, b % best_str); n['best'] += k
    h = h.replace('<div class="value">%s</div><div class="meta">Race pace</div>' % best_str, '<div class="value">%s</div><div class="meta">Race best · %s</div>' % (best_str, best[1]))
    if h != o: open(f, 'w').write(h)
print('race best', best_str, best[1], best[2], '| swapped stints', len(swapped), '| replacements', n)
