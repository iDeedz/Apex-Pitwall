#!/usr/bin/env python3
"""Re-render the baked (static) copies of tyre sets and stints in every page from js/data.js,
so the no-JS HTML, the ticker and the tables can never drift from AX_DATA."""
import json, re, glob
from pathlib import Path
R = Path(__file__).resolve().parent.parent
s = (R / 'js/data.js').read_text(); D = json.loads(s[s.index('{'):s.rindex('}') + 1])
T = {t['set']: t for t in D['tyres']}; I = {t['id']: t for t in D['tyres']}; S = {x['id']: x for x in D['stints']}
def trow(t): return (f'<tr><td><a class="mono" href="tire-set-detail.html">{t["id"]}</a></td><td>{t["set"]}</td><td><span class="badge {t["compound"]}">{t["compound"]}</span></td>'
                     f'<td>{t["age"]} laps</td><td>{t["heat"]}C</td><td>{t["press"]:.1f} psi</td><td>{t["car"]}</td><td><span class="badge {t["status"]}">{t["status"]}</span></td></tr>')
def srow(x, drv=True): return (f'<tr><td><a class="mono" href="stint-detail.html">{x["id"]}</a></td>' + (f'<td>{x["driver"]}</td>' if drv else '') +
                     f'<td><span class="badge {x["compound"]}">{x["compound"]}</span></td><td>{x["laps"]}</td><td>{x["avg"]}</td><td>{x["best"]}</td><td>{x["wear"]}%</td><td><span class="badge {x["status"]}">{x["status"]}</span></td></tr>')
RULES = [
 (r'<tr><td><a class="mono" href="tire-set-detail.html">(TYR-\d{3})</a></td>.*?</tr>', lambda m: trow(I[m.group(1)])),
 (r'<span class="[A-Z]+">(S\d\d) [A-Z]+ · \d+C · [\d.]+ psi · [A-Za-z]+</span>', lambda m: (lambda t: f'<span class="{t["compound"]}">{t["set"]} {t["compound"]} · {t["heat"]}C · {t["press"]:.1f} psi · {t["status"]}</span>')(T[m.group(1)])),
 (r'<div class="tyre-pill [A-Z]+">(S\d\d) · [A-Z]+ · [A-Za-z]+</div>', lambda m: (lambda t: f'<div class="tyre-pill {t["compound"]}">{t["set"]} · {t["compound"]} · {t["status"]}</div>')(T[m.group(1)])),
 (r'<span class="[A-Z]+">\[(ST-\d{3})\] [A-Z]{3} · [A-Z]+ · \d+ laps · wear \d+% · [A-Za-z]+</span>', lambda m: (lambda x: f'<span class="{x["compound"]}">[{x["id"]}] {x["driver"]} · {x["compound"]} · {x["laps"]} laps · wear {x["wear"]}% · {x["status"]}</span>')(S[m.group(1)])),
 (r'<tr><td><a class="mono" href="stint-detail.html">(ST-\d{3})</a></td><td>[A-Z]{3}</td><td><span class="badge [A-Z]+">[A-Z]+</span></td><td>\d+</td><td>[\d:.]+</td><td>[\d:.]+</td><td>\d+%</td><td><span class="badge [A-Za-z]+">[A-Za-z]+</span></td></tr>', lambda m: srow(S[m.group(1)])),
 (r'<tr><td><a class="mono" href="stint-detail.html">(ST-\d{3})</a></td><td><span class="badge [A-Z]+">[A-Z]+</span></td><td>\d+</td><td>[\d:.]+</td><td>[\d:.]+</td><td>\d+%</td><td><span class="badge [A-Za-z]+">[A-Za-z]+</span></td></tr>', lambda m: srow(S[m.group(1)], False)),
 (r'(ST-\d{3}) · ([A-Z]{3})</strong><div class="meta">[A-Z]+ · \d+ laps · best [\d:.]+</div>', lambda m: (lambda x: f'{x["id"]} · {x["driver"]}</strong><div class="meta">{x["compound"]} · {x["laps"]} laps · best {x["best"]}</div>')(S[m.group(1)])),
]
changed = 0
for f in sorted(glob.glob(str(R / '*.html'))):
    h = open(f).read(); o = h
    for pat, fn in RULES: h = re.sub(pat, fn, h)
    if h != o: open(f, 'w').write(h); changed += 1
print('pages updated:', changed)
