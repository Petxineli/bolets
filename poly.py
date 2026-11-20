"""Puntua cada polígon de bosc del mapa d'hàbitats i el reparteix en tessel·les per al mapa.

Entrades: data/boscos-catalunya.json, data/cells.txt, data/meteo_estacions.json, score.py (funcions)
Sortida:  site/t/<tx>_<ty>.json, site/habitats.json, site/meteo.json
"""
import json, math, os, re, sys, collections

src = open('score.py').read().split('\ncells = []')[0]
exec(src)  # TEMP, NOM, habitat(), temp_factor(), rain_factor(), meteo_cell(), dec(), G, ALPHA, FIELDS...

ORDER = ['rovello', 'pinetell', 'camagroc', 'llenega', 'fredolic', 'trompeta', 'carlet', 'cep', 'oureig', 'murgola']
TILE = 0.25
import os
FOC = json.load(open('data/foc.json')) if os.environ.get('USE_FIRES')=='1' else []  # zones cremades desactivades fins a la primavera
for f in FOC: f['r'] = round(math.sqrt(f['ha'] * 1e4 / math.pi))


def burn_idx(lon, lat):
    for k, f in enumerate(FOC):
        dx = (lon - f['lon']) * 111320 * math.cos(math.radians(lat)); dy = (lat - f['lat']) * 110540
        if dx * dx + dy * dy <= f['r'] ** 2: return k + 1
    return 0

# ---------------------------------------------------------------- classificació del text de l'hàbitat
def classify(t):
    t = (t or '').lower()
    trees = []
    if re.search(r'pi roig|pinus sylvestris', t): trees.append('PR')
    if re.search(r'pi negre|pinus uncinata', t): trees.append('PN')
    if re.search(r'pi blanc|pinus halepensis', t): trees.append('PB')
    if re.search(r'pinassa|pinus nigra|pi pinyer|pinus pinea|pinastre|pinus pinaster|pinus spp|altres boscos mixtos de coníferes', t): trees.append('PO')
    if re.search(r'fageda|fagus|avet|abies', t): trees.append('FA')
    if re.search(r'roure|roured|quercus (humilis|pubescens|petraea|robur|pyrenaica|faginea|canariensis|cerrioides|x cerrioides)|caducifolis', t): trees.append('RO')
    if re.search(r'alzin|carrasc|surer|sured|quercus (ilex|suber|rotundifolia)', t): trees.append('AL')
    if re.search(r'castany', t): trees.append('CA')
    c = {k: 0.0 for k in FIELDS}
    for k in trees: c[k] = 1 / len(trees)
    if re.search(r'acidòfil|silicícol|terreny silici', t): c['acid'] = 1
    if re.search(r'calcícol|neutrobasòfil|basòfil|terreny calcari', t): c['calc'] = 1
    if re.search(r'obac|ombrívol', t): c['obac'] = 1
    if re.search(r'sense sotabosc', t): c['open'] = 1
    info = dict(solell=bool(re.search(r'solell', t)), xero=bool(re.search(r'xeròfil|poc plujosa', t)),
                humit=bool(re.search(r'higròfil|mesohigròfil', t)))
    stage = 'subalp' if 'subalp' in t else 'submont' if 'submont' in t else 'mont' if re.search(r'montà|muntanya mitjana|muntanyenc', t) else 'baixa' if re.search(r'terra baixa|marítim|litoral', t) else None
    return c, info, stage, bool(trees)


raw = json.load(open('data/boscos-catalunya.json'))
codes = list(raw['codes'].keys())
cidx = {k: i for i, k in enumerate(codes)}
CL = {k: classify(raw['codes'][k]) for k in codes}

# altitud per cel·la de 5 km (de cells.txt)
elev = {}
for line in open('data/cells.txt'):
    line = line.strip()
    if len(line) < 20: continue
    i, j = ALPHA.index(line[0]), ALPHA.index(line[1])
    elev[(i, j)] = int(line[14:16], 36) * 10

meteo_cache = {}


def meteo_for(i, j, e):
    k = (i, j)
    if k not in meteo_cache:
        lon = G['lon0'] + (i + .5) * G['dlon']; lat = G['lat0'] + (j + .5) * G['dlat']
        meteo_cache[k] = (meteo_cell(lon, lat, e), e)
    return meteo_cache[k]


def adjust_elev(e, stage):
    if stage == 'subalp': return max(e, 1700)
    if stage == 'mont': return min(max(e, 800), 1700)
    if stage == 'submont': return min(max(e, 400), 1100)
    if stage == 'baixa': return min(e, 800)
    return e


tiles = collections.defaultdict(list)
stats = collections.Counter()
for code, area, polys in raw['feats']:
    c, info, stage, isforest = CL[code]
    if not isforest: continue
    # centroide aproximat: primer anell exterior
    ring = polys[0][0]
    x = y = 0; xs = []; ys = []
    for k in range(0, len(ring), 2):
        x += ring[k]; y += ring[k + 1]; xs.append(x); ys.append(y)
    lon = sum(xs) / len(xs) / 1e4; lat = sum(ys) / len(ys) / 1e4
    i = int((lon - G['lon0']) / G['dlon']); j = int((lat - G['lat0']) / G['dlat'])
    e0 = elev.get((i, j))
    if e0 is None:
        near = [elev[k] for k in [(i + a, j + b) for a in (-1, 0, 1) for b in (-1, 0, 1)] if k in elev]
        e0 = round(sum(near) / len(near)) if near else 600
    burn = burn_idx(lon, lat)
    m, ecell = meteo_for(i, j, e0)
    e = adjust_elev(e0, stage)
    tn = m['tn7'] - (e - ecell) / 150; tx = m['tx7'] - (e - ecell) / 150; tnmin = m['tnmin7'] - (e - ecell) / 150
    tmean = (tn + tx) / 2
    sc = []
    for g in ORDER:
        s = TEMP[g].get(MONTH, 0)
        if s == 0: sc.append(0); continue
        h = habitat(g, c)
        if g == 'murgola' and burn: h = max(h, .7)  # bosc cremat fa poc: la múrgola surt 1-2 anys després del foc
        if info['xero'] and g != 'rovello': h *= .85
        if info['humit'] and g in ('trompeta', 'camagroc', 'cep'): h = min(1, h * 1.1)
        if info['solell'] and g == 'rovello' and MONTH >= 11: h = min(1, h * 1.05)
        if g in ('rovello', 'pinetell') and c['open'] and (c['PR'] or c['PB'] or c['PO'] or c['PN']):
            h = min(1, h * 1.15)  # «el sant grial»: pineda sense sotabosc
        t = temp_factor(g, tmean, tn, tnmin)
        r = rain_factor(g, m)
        v = 1.0
        if m['dies_vent7'] >= 3: v = .8 if e < 1500 else .65
        sc.append(round(100 * h * s * (.15 + .85 * r) * t * v))
    best = max(sc)
    stats[min(9, best // 10)] += 1
    tk = f"{int((lon - G['lon0']) // TILE)}_{int((lat - G['lat0']) // TILE)}"
    rec = [cidx[code], f'{i}_{j}', e, round(area / 1e4, 1), sc, polys]
    if burn: rec.append(burn)
    tiles[tk].append(rec)

os.makedirs('site/t', exist_ok=True)
for f in os.listdir('site/t'): os.remove('site/t/' + f)
sizes = []
for tk, items in tiles.items():
    s = json.dumps(items, separators=(',', ':'))
    open(f'site/t/{tk}.json', 'w').write(s); sizes.append(len(s))
json.dump(dict(order=ORDER, codes=[raw['codes'][k] for k in codes], tile=TILE, lon0=G['lon0'], lat0=G['lat0'],
               tiles=sorted(tiles.keys()), foc=FOC),
          open('site/habitats.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump({f'{i}_{j}': dict(m={k: (round(v, 1) if isinstance(v, float) else v) for k, v in m.items()}, e=e)
           for (i, j), (m, e) in meteo_cache.items()},
          open('site/meteo.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('polígons', sum(len(v) for v in tiles.values()), 'tessel·les', len(tiles), 'MB', round(sum(sizes) / 1e6, 1), 'max', max(sizes))
print(sorted(stats.items()))
