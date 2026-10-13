import json,re,glob,collections,sys
import os;R=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')+'/'
def load(p):
    s=open(R+p).read();return json.loads(s[s.index('{'):s.rindex('}')+1])
D=load('js/data.js');E=load('js/data-extra.js')
sec=lambda s:int(s.split(':')[0])*60+float(s.split(':')[1])
fails=[];best=sec(D['kpis']['best_lap'])
st={s['id']:s for s in D['stints']}
for l in E['laps']:
    if abs(l['s1']+l['s2']+l['s3']-l['t'])>0.0005: fails.append('E.lap sum %s'%l)
for t in D['tower']:
    if abs(t['s1']+t['s2']+t['s3']-sec(t['last']))>0.0005: fails.append('tower sum '+t['code'])
for s in D['stints']:
    if '—' not in (s['best'],s['avg']) and sec(s['best'])>sec(s['avg']): fails.append('stint best>avg '+s['id'])
fast=collections.Counter()
for f in sorted(glob.glob(R+'*.html')):
    h=open(f).read();n=f.split('/')[-1]
    for m in re.finditer(r'<tr><td>(\d+)</td><td>([A-Z]{3})</td><td>(\d:\d\d\.\d{3})</td><td>([\d.]+)</td><td>([\d.]+)</td><td>([\d.]+)</td>',h):
        if abs(sec(m.group(3))-sum(float(m.group(i)) for i in (4,5,6)))>0.0005: fails.append(n+' row '+m.group(0)[:60])
    for m in re.finditer(r'(ST-\d{3})</a></td><td>([A-Z]{3})</td>(?:(?!</tr>).)*?</td><td>(\d+)</td><td>(\d:\d\d\.\d{3})</td><td>(\d:\d\d\.\d{3})</td>',h):
        s=st[m.group(1)]
        if (s['avg'],s['best'])!=(m.group(4),m.group(5)): fails.append(n+' stint row '+m.group(1))
    for m in re.finditer(r'(ST-\d{3}) · ([A-Z]{3})</strong><div class="meta">[^<]*?best (\d:\d\d\.\d{3})',h):
        if st[m.group(1)]['best']!=m.group(3): fails.append(n+' stint card '+m.group(1))
    for m in re.finditer(r'Best lap</div><div class="value">([^<]+)</div><div class="meta">Race best · ([A-Z]+)',h):
        if (m.group(1),m.group(2))!=(D['kpis']['best_lap'],D['kpis']['best_lap_by']): fails.append(n+' best kpi')
    # any 'Avg X' / 'Best Y' pair inside one card group must have best <= avg
    for m in re.finditer(r'Avg</div><div class="value">(\d:\d\d\.\d{3})</div>.{0,400}?Best</div><div class="value">(\d:\d\d\.\d{3})',h):
        if sec(m.group(2))>sec(m.group(1)): fails.append(n+' best slower than avg '+m.group(0)[:40])
    for m in re.finditer(r'(\d:\d\d\.\d{3})</div><div class="meta">Avg (\d:\d\d\.\d{3})',h):
        if sec(m.group(1))>sec(m.group(2)): fails.append(n+' best slower than avg (meta)')
    for t in D['tower']:
        m=re.search(r'data-code="%s"><div class="pos">P(\d) <b>([^<]+)</b>'%t['code'],h)
        if m and (int(m.group(1))!=t['pos'] or m.group(2)!=t['last']): fails.append(n+' tower '+t['code'])
    # every lap time on every page: nothing may beat the race best unless it is explicitly a qualifying or circuit-record time
    for m in re.finditer(r'(?<![\d:.])(\d:\d\d\.\d{3})(?![\d])',h):
        if sec(m.group(1))>=best-1e-9: continue
        row=h.rfind('<tr',0,m.start());card=max(h.rfind('class="kpi-card',0,m.start()),h.rfind('<li',0,m.start()),h.rfind('<span',0,m.start()-1))
        if row>h.rfind('</tr>',0,m.start()):
            th=h.rfind('<thead',0,row);ctx=re.sub(r'<[^>]+>',' ',h[th:h.find('</thead>',th)] if th>=0 else '')+' | '+re.sub(r'<[^>]+>',' ',h[row:m.start()])
        else: ctx=re.sub(r'<[^>]+>',' ',h[max(card,m.start()-300):m.start()])
        if re.search(r'\b(Q[123]|SES-Q\d|[Qq]ualif\w*|[Rr]ecord|[Pp]ole)\b',ctx): fast['allowed: '+re.sub(r'\s+',' ',ctx.strip())[:70]]+=1
        else: fails.append('%s faster than race best: %s (ctx: %s)'%(n,m.group(1),ctx.strip()[-60:]))
for l in E['laps']:
    if l['t']<best-1e-9: fails.append('E.lap faster than race best %s L%s %.3f'%(l['driver'],l['lap'],l['t']))
for s in D['stints']:
    if s['best']!='—' and sec(s['best'])<best-1e-9: fails.append('stint best faster than race best '+s['id'])
for t in D['tower']:
    if sec(t['last'])<best-1e-9: fails.append('tower faster than race best '+t['code'])
# weather number book: one wind value/direction, one track status, one rain cell everywhere
WX={'wind':str(D['kpis']['wind_kts'])+' kts'}
for f in sorted(glob.glob(R+'*.html')):
    h=open(f).read();n=f.split('/')[-1]
    dirs=set(re.findall(r'Tail [A-Z]\d',h))
    if len(dirs)>1: fails.append(n+' wind direction differs: '+','.join(sorted(dirs)))
    for m in re.finditer(r'Wind</div><div class="value[^"]*"[^>]*>([^<]+)</div>',h):
        if m.group(1).strip()!=WX['wind']: fails.append(n+' wind value '+m.group(1))
    tr=set(m.group(1) for m in re.finditer(r'label">Track</div><div class="value[^"]*"[^>]*>%dC</div><div class="meta">([^<]+)'%D['kpis']['track_temp'],h))
    if len(tr)>1: fails.append(n+' track status differs: '+','.join(sorted(tr)))
    rc=set(m.group(1) for m in re.finditer(r'label">Rain[^<]*</div><div class="value[^"]*"[^>]*>%d%%</div><div class="meta">([^<]+)'%D['kpis']['rain_pct'],h))
    if len(rc)>1: fails.append(n+' rain cell differs: '+','.join(sorted(rc)))

# ---- cross-page number book: every baked copy must agree with AX_DATA ----
txt=lambda x:re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',x)).strip()
SES={x['id']:x for x in D['sessions']};SESN={x['name']:x for x in D['sessions']}
STR={x['car']:x for x in D['strategy']};TY={t['id']:t for t in D['tyres']};TS={t['set']:t for t in D['tyres']};STI={x['id']:x for x in D['stints']}
DRV={d['code']:d for d in D['drivers']};DRN={d['num']:d for d in D['drivers']}
K=D['kpis'];C=collections.Counter(t['status'] for t in D['tyres'])
# data-level rules
for car in D['cars']:
    d=DRN[int(car['id'][4:])];m=[t for t in D['tyres'] if t['car']==car['id'] and t['status']=='Mounted']
    if len(m)!=1 or m[0]['compound']!=d['tyre']: fails.append('data: %s mounted sets %s (driver on %s)'%(car['id'],[t['compound'] for t in m],d['tyre']))
for code,d in DRV.items():
    a_=[x for x in D['stints'] if x['driver']==code and x['status']=='Active']
    if len(a_)>1 or (a_ and a_[0]['compound']!=d['tyre']): fails.append('data: %s active stints %s (on %s)'%(code,[(x['id'],x['compound']) for x in a_],d['tyre']))
for st in D['strategy']:
    d=DRN[int(st['car'][1:])];seq=st['compounds'].split('-')
    if len(seq)!=st['stops']+1: fails.append('data: %s %s has %d stints for %d stops'%(st['car'],st['compounds'],len(seq),st['stops']))
    if d['stint']>len(seq) or seq[d['stint']-1]!=d['tyre'][0]: fails.append('data: %s plan %s stint %d is not %s'%(st['car'],st['compounds'],d['stint'],d['tyre']))
# stat cards whose meaning is global: value must equal the number book
EXP={'Track':'%dC'%K['track_temp'],'Track temp':'%dC'%K['track_temp'],'Air':'%dC'%K['air_temp'],'Rain':'%d%%'%K['rain_pct'],'Rain risk':'%d%%'%K['rain_pct'],
 'Wind':'%d kts'%K['wind_kts'],'Humidity':'%d%%'%K['humidity'],'Pit loss':'%.1fs'%K['pit_loss'],'Open alerts':str(K['alerts_open']),'Best lap':K['best_lap'],
 'Tyre sets':str(len(D['tyres'])),'Sets':str(len(D['tyres'])),'Stints':str(len(D['stints'])),'Incidents':str(len(D['incidents'])),'Laps taped':str(len(E['laps'])),
 'Mounted':str(C['Mounted']),'Cage':str(C['Cage']),'Alerts':str(len(D['alerts'])),'Archive':str(len(D['alerts'])),'Cleared':str(sum(1 for x in D['alerts'] if x['status']=='Closed')),
 'Crit':None,'Lap':'%d / %d'%(K['lap'],K['total_laps']),'Drivers':str(len(D['drivers'])),'Guests':str(len(D['guests'])),'Party':str(len(D['guests'])),'Seals':str(len(D['parts'])),
 'Cars':str(len(D['cars'])),'Circuits':str(len(D['circuits'])),'Partners':str(len(D['sponsors'])),'Crew':None,'Open book':str(len(D['incidents']))}
for f in sorted(glob.glob(R+'*.html')):
    h=open(f).read();n=f.split('/')[-1]
    for m in re.finditer(r'<div class="kpi-card[^"]*"><div class="label">([^<]+)</div><div class="value[^"]*"[^>]*>([^<]*)</div>(?:<div class="meta">([^<]*)</div>)?',h):
        lab,val,meta=m.group(1).strip(),m.group(2).strip(),(m.group(3) or '').strip()
        if EXP.get(lab) and val and val!=EXP[lab]: fails.append('%s card %s = %s, book says %s'%(n,lab,val,EXP[lab]))
        if lab=='Session' and val in SESN and meta and meta not in ('Complete','Planned','LIVE','Live') : pass
        if lab=='Session' and val in SESN and meta in ('Complete','Planned','LIVE','Live') and meta.lower()!=SESN[val]['status'].lower(): fails.append('%s session card %s %s vs %s'%(n,val,meta,SESN[val]['status']))
        if lab=='Next' and val in SESN and SESN[val]['status']!='Planned': fails.append('%s Next=%s but it is %s'%(n,val,SESN[val]['status']))
    # header says which session this page is about: its session card must match
    hd=re.search(r'<h1>Session detail · (\w+)',h)
    if hd:
        for m in re.finditer(r'<div class="label">Session</div><div class="value[^"]*"[^>]*>([^<]+)<',h):
            if m.group(1)!=hd.group(1): fails.append('%s header %s but session card %s'%(n,hd.group(1),m.group(1)))
    for m in re.finditer(r'<tr><td>(?:<a[^>]*>)?(SES-[A-Z0-9]+)(?:</a>)?</td>(.*?)</tr>',h):
        x=SES[m.group(1)];cells=[txt(c) for c in re.findall(r'<td>(.*?)</td>',m.group(2))]
        for want in (x['status'],x['best']):
            if want not in cells: fails.append('%s session row %s missing %s (%s)'%(n,x['id'],want,cells))
    for m in re.finditer(r'<tr><td>(#\d\d)</td><td>(.*?)</tr>',h):
        if m.group(1) not in STR: continue
        x=STR[m.group(1)];cells=[txt(c) for c in re.findall(r'<td>(.*?)</td>','<td>'+m.group(2))]
        for want in (x['plan'],str(x['stops']),x['compounds'],x['win'],x['risk']):
            if want not in cells: fails.append('%s plan row %s missing %s (%s)'%(n,x['car'],want,cells))
    for m in re.finditer(r'<strong>(#\d\d)</strong><div class="meta">([^<]+)</div></div><span class="badge">(\w)</span>',h):
        x=STR.get(m.group(1))
        if x and (m.group(2)!='%s · %s'%(x['compounds'],x['win']) or m.group(3)!=x['plan']): fails.append('%s strategy card %s'%(n,m.group(0)[:60]))
    if n=='strategy-sim.html':
        b=STR['#11']
        r_=re.search(r'label">Risk</div><div class="value">(\w+)',h)
        if r_ and r_.group(1)!=b['risk']: fails.append('strategy-sim risk %s vs plan %s'%(r_.group(1),b['risk']))
        if '#11 '+b['compounds'] not in h: fails.append('strategy-sim baseline compounds')
    for m in re.finditer(r'<tr><td><a class="mono" href="tire-set-detail.html">(TYR-\d{3})</a></td>(.*?)</tr>',h):
        t=TY[m.group(1)];cells=[txt(c) for c in re.findall(r'<td>(.*?)</td>',m.group(2))]
        if [t['set'],t['compound'],t['car'],t['status']]!=[cells[0],cells[1],cells[5],cells[6]]: fails.append('%s tyre row %s %s'%(n,t['id'],cells))
    for m in re.finditer(r'(S\d\d)(?: | · )([A-Z]+) · (?:\d+C · [\d.]+ psi · )?([A-Za-z]+)</',h):
        t=TS[m.group(1)]
        if (m.group(2),m.group(3))!=(t['compound'],t['status']): fails.append('%s tyre %s %s/%s vs %s/%s'%(n,t['set'],m.group(2),m.group(3),t['compound'],t['status']))
    for m in re.finditer(r'\[(ST-\d{3})\] ([A-Z]{3}) · ([A-Z]+) · (\d+) laps · wear (\d+)% · (\w+)<',h):
        x=STI[m.group(1)]
        if (m.group(2),m.group(3),int(m.group(4)),int(m.group(5)),m.group(6))!=(x['driver'],x['compound'],x['laps'],x['wear'],x['status']): fails.append('%s ticker stint %s'%(n,x['id']))
    for m in re.finditer(r'<tr><td><a class="mono" href="stint-detail.html">(ST-\d{3})</a></td>(.*?)</tr>',h):
        x=STI[m.group(1)];cells=[txt(c) for c in re.findall(r'<td>(.*?)</td>',m.group(2))]
        for want in (x['compound'],str(x['laps']),x['best'],x['status']):
            if want not in cells: fails.append('%s stint row %s missing %s'%(n,x['id'],want))
    # classification rows: tyre / gap / fuel / ers / wear / status per driver
    for m in re.finditer(r'<tr><td><a class="mono" href="driver-detail.html">([A-Z]{3})</a></td><td>#(\d+)</td>(.*?)</tr>',h):
        d=DRV[m.group(1)];cells=[txt(c) for c in re.findall(r'<td>(.*?)</td>',m.group(3))]
        for want in (d['tyre'],d['gap'],d['status']):
            if want not in cells: fails.append('%s driver row %s missing %s'%(n,d['code'],want))
        if len(cells)>=9 and (cells[5],cells[6],cells[7])!=('%d%%'%d['fuel_pct'],'%d%%'%d['ers'],'%d%%'%d['wear']): fails.append('%s driver row %s fuel/ers/wear %s'%(n,d['code'],cells[5:8]))

# ---- derivations: everything below is recomputed from the lap tape alone ----
fmt=lambda t:'%d:%06.3f'%(int(t//60),t-60*int(t//60))
LET={'S':'SOFT','M':'MEDIUM','H':'HARD','I':'INTER','W':'WET'};DRY=('SOFT','MEDIUM','HARD')
NOW,TOT=K['lap'],K['total_laps'];PL={int(p['car'][1:]):[LET[c] for c in p['compounds'].split('-')] for p in D['strategy']}
tape=collections.defaultdict(list)
for l in E['laps']: tape[l['driver']].append(l)
if max(l['lap'] for l in E['laps'])>NOW: fails.append('tape: laps beyond race lap %d'%NOW)
for code,d in DRV.items():
    # checks that need only the stint book + driver record (run even when the tape is unusable)
    run0=[s for s in D['stints'] if s['driver']==code and s['status']!='Queued']
    if len(run0)!=d['stint']: fails.append('stints: %s has %d run stints, driver.stint %d'%(code,len(run0),d['stint']))
    if sum(s['laps'] for s in run0)!=d['laps']: fails.append('stints: %s run stint laps %d vs %d race laps'%(code,sum(s['laps'] for s in run0),d['laps']))
    if d['num'] in PL and [s['compound'] for s in run0]!=PL[d['num']][:len(run0)]: fails.append('stints: %s compounds %s vs plan %s'%(code,[s['compound'][0] for s in run0],'-'.join(c[0] for c in PL[d['num']])))
    if any(s['compound'] not in DRY for s in run0) and all(s['compound'] in DRY for s in run0[-1:]) : fails.append('stints: %s ran a wet/inter stint in a dry race'%code)
    car_='CAR-%02d'%d['num'];m_=[t for t in D['tyres'] if t['car']==car_ and t['status']=='Mounted']
    if m_ and run0 and m_[0]['age']!=run0[-1]['laps']: fails.append('tyres: %s mounted %s age %d vs active stint %d laps'%(car_,m_[0]['id'],m_[0]['age'],run0[-1]['laps']))
    T_=sorted(tape.get(code,[]),key=lambda l:l['lap'])
    if [l['lap'] for l in T_]!=list(range(1,d['laps']+1)): fails.append('tape: %s laps %s.. vs driver.laps %d'%(code,[l['lap'] for l in T_][:3],d['laps']));continue
    if any('stint' not in l or 'compound' not in l for l in T_): fails.append('tape: %s laps carry no compound/stint'%code);continue
    groups=[];[groups.append([]) or None for _ in range(max(l['stint'] for l in T_))]
    for l in T_: groups[l['stint']-1].append(l)
    if len(groups)!=d['stint']: fails.append('tape: %s has %d stints, driver.stint %d'%(code,len(groups),d['stint']))
    comps=[g[0]['compound'] for g in groups]
    if any(len({l['compound'] for l in g})!=1 for g in groups): fails.append('tape: %s compound changes inside a stint'%code)
    if comps[-1]!=d['tyre']: fails.append('tape: %s current compound %s vs tyre %s'%(code,comps[-1],d['tyre']))
    if d['num'] in PL and PL[d['num']][:len(comps)]!=comps: fails.append('tape: %s compounds %s vs plan %s'%(code,comps,PL[d['num']]))
    for gi,g in enumerate(groups):
        if gi<len(groups)-1 and g[-1].get('pit')!='in': fails.append('tape: %s stint %d has no in-lap'%(code,gi+1))
        if gi>0 and g[0].get('pit')!='out': fails.append('tape: %s stint %d has no out-lap'%(code,gi+1))
    run=[s for s in D['stints'] if s['driver']==code and s['status']!='Queued']
    if len(run)!=len(groups): fails.append('stints: %s has %d run stints, tape %d'%(code,len(run),len(groups)))
    for s,g in zip(run,groups):
        ts=[l['t'] for l in g]
        want=(g[0]['compound'],len(g),fmt(sum(ts)/len(ts)),fmt(min(ts)))
        if (s['compound'],s['laps'],s['avg'],s['best'])!=want: fails.append('stints: %s %s %s vs tape %s'%(code,s['id'],(s['compound'],s['laps'],s['avg'],s['best']),want))
        if s.get('from')!=g[0]['lap'] or s.get('to')!=g[-1]['lap']: fails.append('stints: %s %s lap range'%(code,s['id']))
    if run and (run[-1]['status']!='Active' or run[-1]['wear']!=d['wear']): fails.append('stints: %s active stint status/wear'%code)
    if any(s['status']=='Active' for s in run[:-1]): fails.append('stints: %s earlier stint still Active'%code)
    for q in [s for s in D['stints'] if s['driver']==code and s['status']=='Queued']:
        if q['laps']>TOT-NOW or (d['num'] in PL and (len(PL[d['num']])<=d['stint'] or q['compound']!=PL[d['num']][d['stint']])): fails.append('stints: %s queued %s does not fit plan/race'%(code,q['id']))
    if code in {t['code'] for t in D['tower']}:
        tw=next(t for t in D['tower'] if t['code']==code)
        if abs(T_[-1]['t']-sec(tw['last']))>0.0005: fails.append('tape: %s last lap %s vs tower %s'%(code,fmt(T_[-1]['t']),tw['last']))
fl=min(E['laps'],key=lambda l:l['t'])
if fmt(fl['t'])!=K['best_lap'] or fl['driver']!=K['best_lap_by']: fails.append('race best %s %s vs tape fastest %s %s'%(K['best_lap'],K['best_lap_by'],fmt(fl['t']),fl['driver']))
if fl.get('compound') not in DRY: fails.append('race best set on %s, not a dry tyre'%fl.get('compound'))
if SES['SES-RACE']['best']!=K['best_lap'] or SES['SES-RACE']['laps']!=NOW: fails.append('SES-RACE best/laps')
if len(D['stints'])!=len({s['id'] for s in D['stints']}): fails.append('stints: duplicate ids')
pur={k:min(E['laps'],key=lambda l:l[k]) for k in ('s1','s2','s3')}
h=open(R+'sector-map.html').read()
for i,k in enumerate(('s1','s2','s3')):
    m=re.search(r'SECTOR %d</div><div class="t">([\d.]+)</div><div class="meta">([^<]+)'%(i+1),h)
    if not m or abs(float(m.group(1))-pur[k][k])>0.0005 or pur[k]['driver'] not in m.group(2): fails.append('sector-map purple %s: %s vs tape %.3f %s'%(k,m.group(1,2) if m else None,pur[k][k],pur[k]['driver']))
# count cards vs the rows they count
CNT={'Stints':len(D['stints']),'Laps taped':len(E['laps']),'Tyre sets':len(D['tyres']),'Incidents':len(D['incidents'])}
RR={'Lap tape':len(E['laps']),'ST-*':len(D['stints']),'TYR-*':len(D['tyres']),'INC-*':len(D['incidents']),'GST-*':len(D['guests']),'RAD-*':len(D['radios']),'PRT-*':len(D['parts']),'ALR-*':len(D['alerts'])}
RR.update({s['name']:s['laps'] for s in D['sessions']})
for f in sorted(glob.glob(R+'*.html')):
    h=open(f).read();n=f.split('/')[-1]
    for lab,v in CNT.items():
        for m in re.finditer(r'<div class="label">%s</div><div class="value[^"]*"[^>]*>(\d+)<'%lab,h):
            if int(m.group(1))!=v: fails.append('%s count card %s=%s, rows %d'%(n,lab,m.group(1),v))
    for m in re.finditer(r'the other (\d+) logged stints',h):
        if int(m.group(1))!=len(D['stints'])-1: fails.append('%s "other %s logged stints"'%(n,m.group(1)))
    for m in re.finditer(r'<thead><tr><th>ID</th><th>Driver</th><th>Compound</th><th>Laps</th><th>Avg</th><th>Best</th><th>Wear</th><th>Status</th></tr></thead><tbody>(.*?)</tbody>',h,re.S):
        ids=re.findall(r'>(ST-\d{3})<',m.group(1))
        if len(ids)!=len(set(ids)) or any(i not in STI for i in ids): fails.append('%s stint table has unknown/duplicate ids'%n)
    for m in re.finditer(r'<thead><tr><th>Lap</th><th>Driver</th>.*?</thead><tbody>(.*?)</tbody>',h,re.S):
        TP={(l['lap'],l['driver']):l for l in E['laps']}
        for r_ in re.finditer(r'<tr><td>(\d+)</td><td>([A-Z]{3})</td><td>([\d:.]+)</td>',m.group(1)):
            l=TP.get((int(r_.group(1)),r_.group(2)))
            if not l or fmt(l['t'])!=r_.group(3): fails.append('%s lap row L%s %s not in tape'%(n,r_.group(1),r_.group(2)));break
    if n=='reports.html':
        i=h.find('<h2>Report index');body=h[i:h.find('</tbody>',i)]
        rows=re.findall(r'<tr><td>[^<]+</td><td>([^<]+)</td><td>(\d+)</td>',body)
        for src,v in rows:
            if src in RR and int(v)!=RR[src]: fails.append('reports index %s rows %s vs data %d'%(src,v,RR[src]))
        pk=re.search(r'label">Packs</div><div class="value[^"]*"[^>]*>(\d+)<',h)
        if pk and int(pk.group(1))!=len(rows): fails.append('reports Packs %s vs %d index rows'%(pk.group(1),len(rows)))
    hd=re.search(r'<h1>Stint detail · (ST-\d{3})</h1><p>([^<]*)</p>',h)
    if hd:
        x=STI[hd.group(1)]
        for lab,v in (('Avg',x['avg']),('Best',x['best']),('Status',x['status'])):
            m=re.search(r'<div class="label">%s</div><div class="value">([^<]*)<'%lab,h)
            if m and m.group(1)!=v: fails.append('stint-detail %s %s vs %s'%(lab,m.group(1),v))
        if '%s · %s · %d laps'%(x['driver'],x['compound'],x['laps']) not in hd.group(2): fails.append('stint-detail header')
# ---- R7: pit status vs plan stops vs stint count ----
SPL={int(p['car'][1:]):p for p in D['strategy']}
def T(s): return re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',s)).strip()
for d in D['drivers']:
    p=SPL.get(d['num']); stops=p['stops'] if p else d['stint']-1
    if p and len(p['compounds'].split('-'))!=stops+1: fails.append('plan: #%d %s has %d stops but %d compounds'%(d['num'],p['compounds'],stops,len(p['compounds'].split('-'))))
    if d['stint']-1>stops: fails.append('pit: %s made %d stops, plan allows %d'%(d['code'],d['stint']-1,stops))
    if d['status']=='PIT' and d['stint']-1>=stops: fails.append('pit: %s shown in pit after %d of %d planned stops (would be an unplanned extra stop)'%(d['code'],d['stint']-1,stops))
    if (d['delta']=='BOX')!=(d['status']=='PIT'): fails.append('pit: %s delta %s vs status %s'%(d['code'],d['delta'],d['status']))
    run=[s for s in D['stints'] if s['driver']==d['code'] and s['status']!='Queued']
    pits=sum(1 for l in tape.get(d['code'],[]) if l.get('pit')=='in')
    if tape.get(d['code']) and pits!=len(run)-1: fails.append('pit: %s tape in-laps %d vs %d stints'%(d['code'],pits,len(run)))
for c in D['cars']:
    dd=[x for x in D['drivers'] if x['name']==c['driver']]
    if dd and c['status']!=dd[0]['status']: fails.append('pit: %s status %s vs driver %s'%(c['id'],c['status'],dd[0]['status']))
npit=sum(1 for d in D['drivers'] if d['status']=='PIT')
for f in sorted(glob.glob(R+'*.html')):
    h=open(f).read();fn=os.path.basename(f)
    for d in D['drivers']:
        for m in re.finditer(r'<strong>%s</strong><span>([A-Z]+) · ([A-Z]+)</span></div><div class="delta ([a-z]+)">([^<]*)'%d['code'],h):
            if m.group(2)!=d['status'] or m.group(4)!=d['delta'] or (m.group(3)=='pit')!=(d['status']=='PIT'): fails.append('pit: %s rail card %s %s/%s vs %s/%s'%(fn,d['code'],m.group(2),m.group(4),d['status'],d['delta']))
    for r in re.findall(r'<tr>(?:(?!</tr>).)*</tr>',h,re.S):
        who=[d for d in D['drivers'] if re.search(r'>%s<|>#%d<|%s|CAR-%02d\b'%(d['code'],d['num'],d['name'],d['num']),r)]
        if len(who)!=1: continue
        for b in re.findall(r'badge (PIT|LIVE)">',r):
            if b!=who[0]['status']: fails.append('pit: %s row for %s says %s, data %s'%(fn,who[0]['code'],b,who[0]['status']))
        if '<td>BOX</td>' in r and who[0]['status']!='PIT': fails.append('pit: %s row for %s shows BOX'%(fn,who[0]['code']))
    for a_,b_ in re.findall(r'(\d+) live · (\d+) pit',h):
        if int(b_)!=npit or int(a_)!=len(D['drivers'])-npit: fails.append('pit: %s field card %s live/%s pit vs %d pit'%(fn,a_,b_,npit))
    if re.search(r'\d+ live · none in pit',h) and npit: fails.append('pit: %s says none in pit'%fn)
# ---- R7: every tyre-set detail card vs AX_DATA.tyres + tape ----
TY={t['id']:t for t in D['tyres']}
for f in sorted(glob.glob(R+'*.html')):
    h=open(f).read();fn=os.path.basename(f);m=re.search(r'<h1>Tyre set · (TYR-\d+)</h1>',h)
    if not m: continue
    t=TY[m.group(1)];d=DRN[int(t['car'][4:])]
    cards={T(a):(T(b),T(c)) for a,b,c in re.findall(r'<div class="kpi-card[^"]*"><div class="label">(.*?)</div><div class="value[^"]*"[^>]*>(.*?)</div><div class="meta">(.*?)</div>',h)}
    want={'Heat':'%dC'%t['heat'],'Press':'%.1f psi'%t['press'],'Age':'%d laps'%t['age'],'Status':t['status'],'Set':t['id'],'Compound':t['compound'],'Driver':d['code'],'Car':t['car']}
    for k,v in want.items():
        if k not in cards: fails.append('tyreset: %s missing card %s'%(fn,k))
        elif cards[k][0]!=v: fails.append('tyreset: %s card %s = %s, data %s'%(fn,k,cards[k][0],v))
    if 'Car' in cards and cards['Car'][1]!=d['status']: fails.append('tyreset: %s car meta %s vs driver status %s'%(fn,cards['Car'][1],d['status']))
    if t['status']=='Mounted':
        a_=[s for s in D['stints'] if s['driver']==d['code'] and s['status']=='Active'][0]
        lp=[l for l in tape.get(d['code'],[]) if l.get('stint')==len([s for s in D['stints'] if s['driver']==d['code'] and s['status']!='Queued'])]
        frm=min(l['lap'] for l in lp) if lp else a_['from']
        if 'Status' in cards and cards['Status'][1]!='Fitted L%d'%frm: fails.append('tyreset: %s %s fitted card "%s" vs tape L%d'%(fn,t['id'],cards['Status'][1],frm))
        if t['age']!=len(lp) and lp: fails.append('tyreset: %s %s age %d vs %d tape laps'%(fn,t['id'],t['age'],len(lp)))
        if 'Age' in cards and re.search(r'L(\d+)–L(\d+)',cards['Age'][1]):
            x,y=map(int,re.search(r'L(\d+)–L(\d+)',cards['Age'][1]).groups())
            if (x,y)!=(frm,max(l['lap'] for l in lp)): fails.append('tyreset: %s age range L%d–L%d vs tape'%(fn,x,y))
    for r in re.findall(r'<tr>(?:(?!</tr>).)*%s(?:(?!</tr>).)*</tr>'%t['id'],h,re.S):
        mm=re.search(r'>(\d+) laps<',r)
        if mm and int(mm.group(1))!=t['age']: fails.append('tyreset: %s table row %s age %s vs %d'%(fn,t['id'],mm.group(1),t['age']))
# ---- R7: every count card vs the table rows it describes (sitewide) ----
PFX={'NOTE':len(E.get('notes',[])),'ALR':len(D['alerts']),'GST':len(D['guests']),'PRT':len(D['parts']),'INC':len(D['incidents']),'TYR':len(D['tyres']),'ST':len(D['stints']),'MED':len(D['media'])}
LABPFX={'note':'NOTE','alert':'ALR','guest':'GST','part':'PRT','incident':'INC','tyre set':'TYR','set':'TYR','stint':'ST','clip':'MED','media':'MED'}
for f in sorted(glob.glob(R+'*.html')):
    h=open(f).read();fn=os.path.basename(f)
    cards=[(T(a),T(b),T(c)) for a,b,c in re.findall(r'<div class="kpi-card[^"]*"><div class="label">(.*?)</div><div class="value[^"]*"[^>]*>(.*?)</div><div class="meta">(.*?)</div>',h)]
    panels=[]
    for m in re.finditer(r'<div class="ax-panel"[^>]*>\s*<h2>(.*?)</h2>(.*?)</table>',h,re.S):
        tb=re.search(r'<tbody[^>]*>(.*?)</tbody>',m.group(2),re.S)
        if not tb: continue
        ids=re.findall(r'<tr><td>(?:<a[^>]*>)?([A-Z]+)-\d+',tb.group(1))
        panels.append((T(m.group(1)),tb.group(1).count('<tr'),collections.Counter(ids).most_common(1)[0][0] if ids else None))
    nums=[(l,int(v.replace(',','')),mt) for l,v,mt in cards if re.fullmatch(r'[\d,]+',v)]
    for lab,v,meta in nums:
        stem=lab.lower().rstrip('s')
        if len(stem)<3: continue
        pf=LABPFX.get(stem)
        for ttl,n,ip in panels:
            linked=(ip==pf) if pf else (stem in ttl.lower())
            if not linked or n==v: continue
            if re.search(r'\bof %d\b'%v,ttl) or re.search(r'\b%d shown\b'%n,meta) or re.search(r'\ball %d\b'%n,ttl): continue
            parts=[int(x) for x in re.findall(r'(\d+) [a-z]+',meta)]
            if len(parts)>1 and sum(parts)==v and n in parts: continue
            sib=sum(v2 for l2,v2,_ in nums if l2.lower().rstrip('s') in ttl.lower())
            if sib==n: continue
            fails.append('count: %s card "%s %d" vs "%s" %d rows (unlabelled sample)'%(fn,lab,v,ttl,n))
        if pf and pf in PFX and v!=PFX[pf] and not any(ip==pf and n==v for _,n,ip in panels) and re.search(r'^(%s)$'%lab,'Notes|Alerts|Guests|Parts|Incidents|Tyre sets|Stints|Clips'):
            fails.append('count: %s card "%s %d" vs data %d'%(fn,lab,v,PFX[pf]))
# ---- R8: physical plausibility of every per-driver live value ----
RATE_={'SOFT':5.5,'MEDIUM':3.5,'HARD':2.4,'INTER':4.5,'WET':4.0}
gs=lambda g:0.0 if not g.startswith('+') else float(g[1:])
dr=sorted(D['drivers'],key=lambda d:d['pos'])
burns=sorted((100-d['fuel_pct'])/d['laps'] for d in dr);medb=burns[len(burns)//2]
for i,d in enumerate(dr):
    L=d['laps'];b=(100-d['fuel_pct'])/L
    if not 1.0<=b<=1.7: fails.append('phys: %s fuel %d%% after %d laps = %.2f%%/lap burn (model 1.0-1.7)'%(d['code'],d['fuel_pct'],L,b))
    if abs(d['fuel_pct']-(100-L*medb))>12: fails.append('phys: %s fuel %d%% vs field model %.0f%%'%(d['code'],d['fuel_pct'],100-L*medb))
    if not 20<=d['ers']<=95: fails.append('phys: %s ERS %d%% outside 20-95'%(d['code'],d['ers']))
    tl=[l for l in tape.get(d['code'],[]) if l['lap']==L]
    if tl and tl[0]['ers']!=d['ers']: fails.append('phys: %s ERS %d vs tape last lap %d'%(d['code'],d['ers'],tl[0]['ers']))
    if gs(d['gap'])>=84: fails.append('phys: %s gap %s is over a lap'%(d['code'],d['gap']))
    if L not in (NOW,NOW-1): fails.append('phys: %s %d laps with gap %s (must be %d or %d)'%(d['code'],L,d['gap'],NOW,NOW-1))
    if i:
        p_=dr[i-1]
        if gs(d['gap'])<=gs(p_['gap']): fails.append('phys: gap order %s %s vs %s %s'%(p_['code'],p_['gap'],d['code'],d['gap']))
        if L>p_['laps']: fails.append('phys: %s P%d has more laps than %s'%(d['code'],d['pos'],p_['code']))
    a_=[s for s in D['stints'] if s['driver']==d['code'] and s['status']=='Active']
    if a_ and abs(d['wear']-a_[0]['laps']*RATE_[d['tyre']])>RATE_[d['tyre']]: fails.append('phys: %s wear %d%% vs %d laps on %s'%(d['code'],d['wear'],a_[0]['laps'],d['tyre']))
for s in D['stints']:
    if s['status']=='Complete' and abs(s['wear']-min(95,s['laps']*RATE_[s['compound']]))>RATE_[s['compound']]: fails.append('phys: %s wear %d%% vs %d laps'%(s['id'],s['wear'],s['laps']))
for i,d in enumerate(dr[1:],1):
    if dr[i-1]['laps']==NOW and d['laps']==NOW-1: pass
cut=[gs(d['gap']) for d in dr if d['laps']==NOW-1]
if cut and max(gs(d['gap']) for d in dr if d['laps']==NOW)>=min(cut): fails.append('phys: lap-count snapshot not consistent with gaps')
AIR=D['kpis']['air_temp'];PST=lambda h:'Hot' if h>=90 else 'Warm' if h>=60 else 'Cold'
for t in D['tyres']:
    s_=t['status'];h_=t['heat']
    ok={'Mounted':h_>=85,'Blanket':60<=h_<=85,'Scrubbed':AIR<=h_<=85,'Cage':AIR<=h_<=AIR+10,'Retired':AIR<=h_<=AIR+10}[s_]
    if not ok: fails.append('phys: %s %s at %dC'%(t['id'],s_,h_))
    if not 19.0<=t['press']<=25.0: fails.append('phys: %s press %.1f'%(t['id'],t['press']))
    if s_=='Mounted' and t['press']<22.0: fails.append('phys: %s mounted but cold pressure %.1f'%(t['id'],t['press']))
    if s_ in ('Scrubbed','Retired') and t['age']<1: fails.append('phys: %s %s with 0 laps'%(t['id'],s_))
for f in sorted(glob.glob(R+'*.html')):
    h=open(f).read();fn=os.path.basename(f)
    m=re.search(r'<h1>Tyre set · (TYR-\d+)</h1>',h)
    if m:
        t=TY[m.group(1)];pm=re.search(r'<div class="label">Press</div><div class="value">[^<]*</div><div class="meta">([^<]*)',h)
        if not pm or pm.group(1)!=PST(t['heat']): fails.append('tyreset: %s press label %s vs heat %dC (%s)'%(fn,pm and pm.group(1),t['heat'],PST(t['heat'])))
        hm=re.search(r'<div class="label">Heat</div><div class="value">[^<]*</div><div class="meta">([^<]*)',h)
        if hm and ('On car' in hm.group(1))!=(t['status']=='Mounted'): fails.append('tyreset: %s heat meta %s vs %s'%(fn,hm.group(1),t['status']))
    # every table that shows Fuel / ERS / Wear for a single driver
    for tb in re.findall(r'<table class="data">(?:(?!</table>).)*</table>',h,re.S):
        if '</thead>' not in tb: continue
        hd=[T(x) for x in re.findall(r'<th[^>]*>(.*?)</th>',tb.split('</thead>')[0])]
        cols={k:i for i,x in enumerate(hd) for k in ('Fuel','ERS','Wear','Laps','Gap') if x==k}
        if 'Fuel' not in cols and 'ERS' not in cols: continue
        if 'Lap' in hd:   # lap tables: per-lap values must equal the tape
            li=hd.index('Lap');di=hd.index('Driver') if 'Driver' in hd else None
            for r in re.findall(r'<tr>(?:(?!</tr>).)*</tr>',tb.split('</thead>')[1],re.S):
                c=[T(x) for x in re.findall(r'<td>((?:(?!</td>).)*)</td>',r,re.S)]
                if len(c)!=len(hd) or di is None: continue
                tl=[l for l in tape.get(c[di],[]) if str(l['lap'])==c[li]]
                if not tl: fails.append('lap: %s row L%s %s not in tape'%(fn,c[li],c[di]));continue
                if 'ERS' in cols and c[cols['ERS']]!='%d%%'%tl[0]['ers']: fails.append('lap: %s L%s %s ERS %s vs tape %d%%'%(fn,c[li],c[di],c[cols['ERS']],tl[0]['ers']))
            continue
        for r in re.findall(r'<tr>(?:(?!</tr>).)*</tr>',tb.split('</thead>')[1],re.S):
            who=[d for d in D['drivers'] if re.search(r'>%s<|>#%d<|%s'%(d['code'],d['num'],d['name']),r)]
            cells=[T(c) for c in re.findall(r'<td>((?:(?!</td>).)*)</td>',r,re.S)]
            if len(who)!=1 or len(cells)!=len(hd): continue
            d=who[0];want={'Fuel':'%d%%'%d['fuel_pct'],'ERS':'%d%%'%d['ers'],'Wear':'%d%%'%d['wear'],'Laps':str(d['laps']),'Gap':d['gap']}
            for k,i in cols.items():
                if cells[i]!=want[k] and not (k=='Gap' and cells[i] in (d['gap'],d['delta'])): fails.append('phys: %s %s %s shows %s, data %s'%(fn,d['code'],k,cells[i],want[k]))
    # free-text "fuel NN%" / "ERS NN%" mentions next to one driver code
    for d in D['drivers']:
        for mm in re.finditer(r'\b%s\b[^<]{0,40}?\b(fuel|ERS)\s*(\d+)%%'%d['code'],h,re.I):
            v=d['fuel_pct'] if mm.group(1).lower()=='fuel' else d['ers']
            if int(mm.group(2))!=v: fails.append('phys: %s text "%s" vs %d%%'%(fn,mm.group(0)[:60],v))
# ---- R9: running order and every gap from cumulative race time ----
CUM={c:{l['lap']:0 for l in v} for c,v in tape.items()}
for c,v in tape.items():
    s_=0
    for l in sorted(v,key=lambda l:l['lap']): s_+=l['t'];CUM[c][l['lap']]=round(s_,3)
dr=sorted(D['drivers'],key=lambda d:d['pos'])
order=sorted(dr,key=lambda d:(-d['laps'],CUM[d['code']][d['laps']]))
if [d['code'] for d in order]!=[d['code'] for d in dr]: fails.append('order: positions %s vs (laps desc, cum asc) %s'%([d['code'] for d in dr],[d['code'] for d in order]))
lead=order[0]['code']
GAP={d['code']:round(CUM[d['code']][d['laps']]-CUM[lead][d['laps']],3) for d in dr}
for d in dr:
    if d['code']==lead:
        if d['gap'] not in ('LEADER','—','0.000'): fails.append('gap: leader %s shows %s'%(d['code'],d['gap']))
        continue
    if abs(gs(d['gap'])-GAP[d['code']])>0.001: fails.append('gap: %s data %s vs cumulative %+.3f'%(d['code'],d['gap'],GAP[d['code']]))
    if GAP[d['code']]>=sec(D['tower'][0]['last'])and d['laps']==dr[0]['laps']: fails.append('gap: %s more than a lap but same lap count'%d['code'])
ivl=[GAP[d['code']]-GAP[p_['code']] for p_,d in zip(dr,dr[1:])]
if any(x<=0 for x in ivl): fails.append('gap: non-positive interval %s'%ivl)
for t in D['tower']:
    if t['code']!=lead and t.get('gap') and abs(gs(t['gap'])-GAP[t['code']])>0.001: fails.append('gap: tower %s %s vs %+.3f'%(t['code'],t['gap'],GAP[t['code']]))
    if t['pos']!=DRV[t['code']]['pos']: fails.append('order: tower %s P%d vs driver P%d'%(t['code'],t['pos'],DRV[t['code']]['pos']))
k2=D['kpis'].get('gap_p2')
if k2 and abs(gs(k2)-GAP[dr[1]['code']])>0.001: fails.append('gap: kpis.gap_p2 %s vs %+.3f'%(k2,GAP[dr[1]['code']]))
for f in sorted(glob.glob(R+'*.html')):
    h=open(f).read();fn=os.path.basename(f)
    for c,pos,g in re.findall(r'data-code="(\w+)"><div class="pos">P(\d+) <b>[^<]*</b></div><div class="name">[^<]*</div><div class="gap">([^<]*)</div>',h):
        if c not in GAP: continue
        if int(pos)!=DRV[c]['pos']: fails.append('order: %s tower cell %s P%s'%(fn,c,pos))
        if c!=lead and abs(gs(g)-GAP[c])>0.001: fails.append('gap: %s tower cell %s %s vs %+.3f'%(fn,c,g,GAP[c]))
    for tb in re.findall(r'<table class="data">(?:(?!</table>).)*</table>',h,re.S):
        if '</thead>' not in tb: continue
        hd=[T(x) for x in re.findall(r'<th[^>]*>(.*?)</th>',tb.split('</thead>')[0])]
        if 'Gap' not in hd: continue
        gi=hd.index('Gap');pi=hd.index('Pos') if 'Pos' in hd else (0 if hd[0] in ('#','P') else None)
        for r in re.findall(r'<tr>(?:(?!</tr>).)*</tr>',tb.split('</thead>')[1],re.S):
            who=[d for d in D['drivers'] if re.search(r'>%s<|>#%d<|%s'%(d['code'],d['num'],d['name']),r)]
            c=[T(x) for x in re.findall(r'<td>((?:(?!</td>).)*)</td>',r,re.S)]
            if len(who)!=1 or len(c)!=len(hd): continue
            d=who[0];g=c[gi]
            if d['code']==lead: ok=g in ('LEADER','—',d['gap'])
            else: ok=g.startswith('+') and abs(gs(g)-GAP[d['code']])<=0.001
            if not ok and g!=d['delta']: fails.append('gap: %s table %s Gap %s vs %+.3f'%(fn,d['code'],g,GAP[d['code']]))
            if pi is not None and re.fullmatch(r'P?\d+',c[pi]) and int(c[pi].lstrip('P'))!=d['pos'] and hd[pi] in ('Pos','P'): fails.append('order: %s table %s pos %s vs %d'%(fn,d['code'],c[pi],d['pos']))
print(json.dumps({'fails':fails,'nfails':len(fails),'best':D['kpis']['best_lap']},indent=1))
for k,v in fast.most_common(40): print(v,repr(k))
