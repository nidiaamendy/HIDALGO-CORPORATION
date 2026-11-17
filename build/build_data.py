"""Convierte las extracciones crudas de Meta Ads en data.json (un bloque por mes).
Uso: python3 build_data.py RAW_DIR data.json  (fusiona con el data.json existente si ya existe)
Archivos esperados en RAW_DIR (respuestas de ads_get_ad_entities):
  account_monthly.json  lista [mes, reach, freq, imp, spend, cpm, eng, thru, clk, lead, conv]
  daily*.txt|json       nivel cuenta, time_increment=1
  camps*.txt|json       nivel campaña, time_increment=monthly
  agegender*.json       nivel cuenta, breakdowns age+gender, monthly
  country*.json         nivel cuenta, breakdown country, monthly
  ads*.txt|json         nivel anuncio, breakdown publisher_platform, monthly
"""
import json, sys, glob, os
from collections import defaultdict

RAW, OUT = sys.argv[1], sys.argv[2]
CONV = 'actions:onsite_conversion.messaging_conversation_started_7d'

def load(f):
    r = json.load(open(f))
    if isinstance(r, list): r = json.loads(r[0]['text'])
    e = r['ad_entities']
    return json.loads(e) if isinstance(e, str) else e

def rows(prefix):
    out = []
    for f in sorted(glob.glob(os.path.join(RAW, prefix + '*'))):
        out += load(f)
    return out

num = lambda v: float(v) if v not in (None, '') else 0.0
inum = lambda v: int(float(v)) if v not in (None, '') else 0
sp = lambda x: num(x['amount_spent']['value']) if x.get('amount_spent') else 0.0
mon = lambda x: x['date_start'][:7]

def result_of(x):
    r = x.get('results') or {}
    ind = r.get('indicator')
    vals = r.get('values') or []
    v = inum(vals[0]['value']) if vals else 0
    return ind, v

RTYPE = {'actions:onsite_conversion.messaging_conversation_started_7d': 'Conversaciones',
         'reach': 'Alcance', 'actions:omni_landing_page_view': 'Visitas a la web',
         'actions:leadgen.other': 'Leads', 'actions:lead': 'Leads',
         'actions:post_engagement': 'Interacciones', 'actions:link_click': 'Clics en el enlace'}
OBJ = {'OUTCOME_SALES': 'Ventas', 'OUTCOME_AWARENESS': 'Reconocimiento', 'OUTCOME_ENGAGEMENT': 'Interacción',
       'OUTCOME_LEADS': 'Clientes potenciales', 'OUTCOME_TRAFFIC': 'Tráfico'}
PLAT = {'facebook': 'Facebook', 'instagram': 'Instagram', 'whatsapp': 'WhatsApp', 'threads': 'Threads',
        'audience_network': 'Audience Network', 'messenger': 'Messenger'}
CTRY = {'BO':'Bolivia','PE':'Perú','AR':'Argentina','CO':'Colombia','EC':'Ecuador','MX':'México','ES':'España','CL':'Chile',
        'FR':'Francia','BR':'Brasil','DE':'Alemania','US':'Estados Unidos','PA':'Panamá','GB':'Reino Unido','UY':'Uruguay',
        'PY':'Paraguay','VE':'Venezuela','CR':'Costa Rica','IT':'Italia','NL':'Países Bajos','CA':'Canadá','GT':'Guatemala',
        'DO':'Rep. Dominicana','SV':'El Salvador','HN':'Honduras','NI':'Nicaragua','CH':'Suiza','BE':'Bélgica','PT':'Portugal'}

data = json.load(open(OUT)) if os.path.exists(OUT) else {'account': 'HIDALGO TOURS BM', 'currency': 'Bs', 'months': {}}
M = defaultdict(dict)

acct_rows = []
if os.path.exists(os.path.join(RAW, 'account_monthly.json')):
    acct_rows = json.load(open(os.path.join(RAW, 'account_monthly.json')))
for x in rows('acct'):
    acct_rows.append([mon(x), inum(x['reach']), num(x['frequency']), inum(x['impressions']), sp(x), num((x.get('cpm') or {}).get('value')),
                      inum(x.get('post_engagement')), inum(x.get('video_thruplay_watched_actions')), inum(x.get('link_click')), inum(x.get('lead')), inum(x.get(CONV))])
for r in acct_rows:
    m, reach, freq, imp, spend, cpm, eng, thru, clk, lead, conv = r
    M[m]['tot'] = dict(reach=reach, freq=freq, imp=imp, spend=spend, cpm=cpm, eng=eng, thru=thru, clk=clk, lead=lead, conv=conv)

daily = defaultdict(dict)
for x in rows('daily'):
    prev = daily[mon(x)].get(x['date_start'])
    if prev and prev['imp'] > 0 and inum(x.get('impressions')) == 0: continue
    daily[mon(x)][x['date_start']] = dict(d=int(x['date_start'][8:]), reach=inum(x['reach']), imp=inum(x['impressions']), spend=round(sp(x), 2),
        eng=inum(x.get('post_engagement')), thru=inum(x.get('video_thruplay_watched_actions')), clk=inum(x.get('link_click')),
        lead=inum(x.get('lead')), conv=inum(x.get(CONV)))
for m, dd in daily.items(): M[m]['daily'] = [dd[k] for k in sorted(dd)]

camps = defaultdict(list)
for x in rows('camps'):
    if sp(x) <= 0: continue
    ind, v = result_of(x); rt = RTYPE.get(ind, '—')
    s = sp(x)
    cpr = (s / v * 1000 if rt == 'Alcance' else s / v) if v else None
    camps[mon(x)].append(dict(name=x['name'], obj=OBJ.get(x.get('objective'), x.get('objective') or ''), spend=round(s, 2),
        reach=inum(x['reach']), imp=inum(x['impressions']), freq=round(num(x['frequency']), 2), cpm=round(num((x.get('cpm') or {}).get('value')), 2),
        rtype=rt, results=v, cpr=round(cpr, 4) if cpr is not None else None, lead=inum(x.get('lead')), conv=inum(x.get(CONV)), eng=inum(x.get('post_engagement'))))
for m, cs in camps.items():
    cs.sort(key=lambda c: -c['spend'])
    gap = M[m]['tot']['spend'] - sum(c['spend'] for c in cs)
    if gap > 1: cs.append(dict(name='Otras (anuncios eliminados)', obj='—', spend=round(gap, 2), reach=0, imp=0, freq=0, cpm=0, rtype='—', results=0, cpr=None, lead=0, conv=0, eng=0))
    M[m]['camps'] = cs

ag = defaultdict(list)
for x in rows('agegender'):
    if x['gender'] not in ('female', 'male') or x['age'] == 'Unknown': continue
    ag[mon(x)].append(dict(age=x['age'], g=x['gender'], reach=inum(x['reach']), imp=inum(x['impressions']), spend=round(sp(x), 2), lead=inum(x.get('lead')), conv=inum(x.get(CONV))))
for m, v in ag.items(): M[m]['ag'] = v

ct = defaultdict(list)
for x in rows('country'):
    if x['country'] == 'unknown' or inum(x['reach']) == 0: continue
    ct[mon(x)].append(dict(c=CTRY.get(x['country'], x['country']), reach=inum(x['reach']), imp=inum(x['impressions']), spend=round(sp(x), 2), lead=inum(x.get('lead')), conv=inum(x.get(CONV))))
for m, v in ct.items(): M[m]['ctry'] = sorted(v, key=lambda c: -c['reach'])

ads = defaultdict(dict); plat = defaultdict(lambda: defaultdict(lambda: dict(imp=0, spend=0.0, lead=0, conv=0, eng=0, clk=0)))
for x in rows('ads'):
    if 'id' not in x: continue
    m = mon(x); p = PLAT.get(x.get('publisher_platform'), None)
    ind, v = result_of(x)
    a = ads[m].setdefault(x['id'], dict(name=x['name'], camp=x.get('campaign_name', ''), spend=0.0, imp=0, results=0, rtype=RTYPE.get(ind, '—'), eng=0, clk=0, lead=0, conv=0, plat={}))
    a['spend'] += sp(x); a['imp'] += inum(x['impressions']); a['results'] += v; a['eng'] += inum(x.get('post_engagement')); a['clk'] += inum(x.get('link_click'))
    a['lead'] += inum(x.get('lead')); a['conv'] += inum(x.get(CONV))
    if p:
        a['plat'][p] = a['plat'].get(p, 0) + inum(x['impressions'])
        P = plat[m][p]; P['imp'] += inum(x['impressions']); P['spend'] += sp(x); P['lead'] += inum(x.get('lead')); P['conv'] += inum(x.get(CONV)); P['eng'] += inum(x.get('post_engagement')); P['clk'] += inum(x.get('link_click'))
for m, d in ads.items():
    top = sorted(d.values(), key=lambda a: -a['imp'])[:12]
    for a in top:
        a['spend'] = round(a['spend'], 2)
        a['cpr'] = round((a['spend'] / a['results'] * 1000 if a['rtype'] == 'Alcance' else a['spend'] / a['results']), 4) if a['results'] else None
        a['ctr'] = round(a['clk'] / a['imp'] * 100, 2) if a['imp'] else 0
    M[m]['ads'] = top
    M[m]['plat'] = sorted([dict(p=k, imp=v['imp'], spend=round(v['spend'], 2), lead=v['lead'], conv=v['conv'], eng=v['eng'], clk=v['clk']) for k, v in plat[m].items() if v['imp'] > 0], key=lambda r: -r['imp'])

for m, v in M.items():
    if 'tot' not in v: continue
    data['months'][m] = {**data['months'].get(m, {}), **v}
data['months'] = dict(sorted(data['months'].items()))
json.dump(data, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
for m, v in data['months'].items():
    print(m, 'gasto', v['tot']['spend'], 'camp', round(sum(c['spend'] for c in v['camps']), 2), 'dias', len(v.get('daily', [])), 'ads', len(v.get('ads', [])),
          'plat_imp', sum(p['imp'] for p in v.get('plat', [])), 'imp', v['tot']['imp'])
