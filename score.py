"""Puntua cada cel·la de 5 km per grup de bolets i genera l'explicació.

Entrades:
  data/cells.txt            cel·les (format compacte exportat del navegador)
  data/meteo_estacions.json indicadors per estació (meteo.py)
Sortida:
  site/cells.json
"""
import json, math, sys, datetime as dt

G = dict(lon0=0.15, lat0=40.50, dlon=0.06, dlat=0.045)
ALPHA = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
B36 = '0123456789abcdefghijklmnopqrstuvwxyz'
FIELDS = ['PR', 'PN', 'PB', 'PO', 'FA', 'RO', 'AL', 'CA', 'acid', 'calc', 'obac', 'open']
TARGET = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date(2026, 11, 21)
MONTH = TARGET.month

NOMS_BOSC = {'PR': 'pi roig', 'PN': 'pi negre', 'PB': 'pi blanc', 'PO': 'altres pins (pinassa, pinyer)',
             'FA': 'faig/avet', 'RO': 'roure', 'AL': 'alzina/surera', 'CA': 'castanyer'}

# ---------------------------------------------------------------- regles per grup
# temporada: factor per mes (1-12)
TEMP = {
    'rovello':  {9: .6, 10: 1, 11: .85, 12: .4},
    'pinetell': {9: .8, 10: 1, 11: .55, 12: .15},
    'cep':      {8: .3, 9: 1, 10: .9, 11: .3, 12: .05},
    'oureig':   {8: .4, 9: 1, 10: .8, 11: .1},
    'camagroc': {9: .6, 10: .9, 11: 1, 12: .8, 1: .4},
    'llenega':  {10: .6, 11: 1, 12: .9, 1: .4},
    'fredolic': {10: .4, 11: 1, 12: .9, 1: .3},
    'trompeta': {9: .4, 10: .9, 11: .9, 12: .4},
    'carlet':   {10: .8, 11: 1, 12: .6},
    'murgola':  {3: .5, 4: 1, 5: 1, 6: .6},
}
NOM = {'rovello': 'Rovelló', 'pinetell': 'Pinetell', 'cep': 'Cep', 'oureig': 'Ou de reig', 'camagroc': 'Camagroc',
       'llenega': 'Llenega negra', 'fredolic': 'Fredolic', 'trompeta': 'Trompeta de la mort', 'carlet': 'Carlet',
       'murgola': 'Múrgola'}
# rang de temperatura mitjana òptima (°C) i perfil
TOPT = {'rovello': (8, 16), 'pinetell': (9, 16), 'cep': (10, 17), 'oureig': (14, 22), 'camagroc': (5, 14),
        'llenega': (4, 13), 'fredolic': (4, 13), 'trompeta': (7, 15), 'carlet': (6, 14), 'murgola': (8, 16)}
TOLERA_FRED = {'camagroc', 'llenega', 'fredolic', 'carlet'}
RESISTENT = {'cep', 'camagroc'}


def cov(x):
    """Una cel·la amb ~40% del bosc adequat ja té zones bones de sobres."""
    return min(1.0, x / 0.6)


def habitat(g, c):
    pins = {'PR': c['PR'], 'PN': c['PN'], 'PB': c['PB'], 'PO': c['PO']}
    acid, calc, obac, open_ = c['acid'], c['calc'], c['obac'], c['open']
    sol_acid = acid / max(acid + calc, 1e-6) if acid + calc > 0.02 else 0.5  # desconegut = 0.5
    sol_calc = 1 - sol_acid
    if g == 'rovello':
        h = cov(c['PR'] + .8 * c['PB'] + .6 * c['PN'] + .7 * c['PO'])
        h *= .75 + .25 * sol_calc
        if MONTH >= 11: h = max(h, cov(c['PB']))  # pi blanc a final de temporada
    elif g == 'pinetell':
        h = cov(c['PR'] + .8 * c['PN'] + .6 * c['PO'] + .3 * c['PB']) * (.6 + .4 * sol_acid)
    elif g == 'cep':
        h = cov(c['PR'] + c['PN'] + c['FA'] + c['CA'] + .5 * (c['AL'] + c['RO'])) * (sol_acid ** 2)
    elif g == 'oureig':
        h = cov(c['AL'] + c['RO'] + c['CA'] + .5 * c['FA']) * sol_acid
    elif g == 'camagroc':
        h = cov(sum(pins.values()) - .5 * c['PB']) * (.8 + .2 * min(1, obac / .15))
    elif g == 'llenega':
        h = cov(sum(pins.values())) * (.6 + .4 * sol_calc)
    elif g == 'fredolic':
        h = cov(sum(pins.values()))
    elif g == 'trompeta':
        h = cov(c['FA'] + .8 * c['RO'] + .7 * c['AL'] + .7 * c['CA']) * (.85 + .15 * min(1, obac / .15))
    elif g == 'carlet':
        h = cov(c['RO'] + .9 * c['AL']) * (.7 + .3 * sol_calc)
    elif g == 'murgola':
        h = cov(c['PN'] + .5 * c['PR'])
    else:
        h = 0
    if g in ('rovello', 'pinetell') and open_ > .05:
        h = min(1, h * 1.1)  # bosc obert / repoblació sense sotabosc
    return h


def temp_factor(g, tmean, tn, tnmin):
    lo, hi = TOPT[g]
    if tmean < lo:
        f = max(0, 1 - (lo - tmean) / 6)
    elif tmean > hi:
        f = max(0, 1 - (tmean - hi) / 6)
    else:
        f = 1
    # gelades
    lim = -2 if g in TOLERA_FRED else 0
    if tnmin < lim - 3: f *= .4
    elif tnmin < lim: f *= .7
    if tn < lim: f *= .5
    return f


def rain_factor(g, m):
    pols = 1 - math.exp(-m['p_pols'] / 35)
    llarg = 1 - math.exp(-m['p30'] / 70)
    if g in RESISTENT:
        return .5 * pols + .5 * llarg
    return .7 * pols + .3 * llarg


# ---------------------------------------------------------------- dades
est = json.load(open('data/meteo_estacions.json'))


def dist(a, b, c, d):
    return math.hypot((a - c) * math.cos(math.radians(41.7)) * 111, (b - d) * 111)


def meteo_cell(lon, lat, elev):
    near = sorted(est.items(), key=lambda kv: dist(lon, lat, kv[1]['lon'], kv[1]['lat']))
    out = {}
    for key, needs in [('rain', 'p_pols'), ('temp', 'tn7'), ('wind', 'dies_vent7')]:
        cand = [(c, m) for c, m in near if needs in m][:3]
        ws = [1 / max(dist(lon, lat, m['lon'], m['lat']), 2) ** 2 for c, m in cand]
        W = sum(ws)
        if key == 'rain':
            for f in ('p_pols', 'p30', 'p_set_oct'):
                out[f] = sum(w * m[f] for w, (c, m) in zip(ws, cand)) / W
            c0, m0 = cand[0]
            out['est_pluja'] = m0['nom']; out['episodi_mm'] = m0['episodi_mm']; out['episodi_dia'] = m0['episodi_dia']
            out['dist_pluja'] = round(dist(lon, lat, m0['lon'], m0['lat']))
        elif key == 'temp':
            # correcció per altitud: -1 °C cada 150 m
            for f in ('tn7', 'tx7', 'tnmin7'):
                out[f] = sum(w * (m[f] - (elev - m['alt']) / 150) for w, (c, m) in zip(ws, cand)) / W
            out['est_temp'] = cand[0][1]['nom']; out['alt_est_temp'] = cand[0][1]['alt']
        else:
            out['dies_vent7'] = sum(w * m['dies_vent7'] for w, (c, m) in zip(ws, cand)) / W
            out['ratxa_max7'] = max(m['ratxa_max7'] for c, m in cand)
    return out


def dec(s):
    return [B36.index(ch) / 35 for ch in s]


cells = []
for line in open('data/cells.txt'):
    line = line.strip()
    if len(line) < 20: continue
    i, j = ALPHA.index(line[0]), ALPHA.index(line[1])
    vals = dec(line[2:14])
    c = dict(zip(FIELDS, vals))
    e = [int(line[k:k + 2], 36) * 10 for k in (14, 16, 18)]
    c['elev'], c['emin'], c['emax'] = e
    lon = G['lon0'] + (i + .5) * G['dlon']; lat = G['lat0'] + (j + .5) * G['dlat']
    forest = sum(c[k] for k in NOMS_BOSC)
    if forest < .08: continue
    # cota de cerca: els bolets es busquen dins el bosc; fem servir la mitjana de la cel·la
    m = meteo_cell(lon, lat, c['elev'])
    tmean = (m['tn7'] + m['tx7']) / 2
    scores, why = {}, {}
    for g in TEMP:
        s = TEMP[g].get(MONTH, 0)
        if s == 0: continue
        h = habitat(g, c)
        if h < .05: continue
        t = temp_factor(g, tmean, m['tn7'], m['tnmin7'])
        r = rain_factor(g, m)
        v = 1.0
        if m['dies_vent7'] >= 3: v = .8 if c['elev'] < 1500 else .65
        sc = 100 * h * s * (.15 + .85 * r) * t * v
        scores[g] = round(sc)
        why[g] = dict(h=round(h, 2), s=s, r=round(r, 2), t=round(t, 2), v=v)
    if not scores: continue
    top = sorted(scores.items(), key=lambda kv: -kv[1])
    total = top[0][1] + (.08 * top[1][1] if len(top) > 1 else 0)
    cells.append(dict(i=i, j=j, lon=round(lon, 3), lat=round(lat, 3), c={k: round(v, 2) for k, v in c.items()},
                      m={k: (round(v, 1) if isinstance(v, float) else v) for k, v in m.items()},
                      tmean=round(tmean, 1), sc=scores, why=why, total=min(100, round(total))))

print(len(cells), 'cel·les amb bosc')
import collections
hist = collections.Counter(min(9, c['total'] // 10) for c in cells)
print(sorted(hist.items()))
best = sorted(cells, key=lambda c: -c['total'])[:12]
for nom,la,lo in [('Vallcebre',42.20,1.82),('Rasos Peguera',42.13,1.73),('Montcalb Solsones',42.10,1.55),('Lluçanès',42.02,2.10),('Puig-Rodó Moianès',41.87,2.10),('Montseny',41.77,2.42),('Montnegre',41.65,2.55),('Gombrèn',42.25,2.08),('Prades',41.31,1.03),('Ports',40.80,0.30),('Val d Aran',42.70,0.80),('Alt Urgell',42.30,1.40)]:
    c=min(cells,key=lambda c:(c['lat']-la)**2+(c['lon']-lo)**2)
    print(nom,c['total'],c['c']['elev'],round(c['tmean'],1),c['m']['p_pols'],c['m']['p30'],sorted(c['sc'].items(), key=lambda kv: -kv[1])[:4])
for c in best:
    print(c['total'], c['lat'], c['lon'], c['c']['elev'], c['m']['est_pluja'], sorted(c['sc'].items(), key=lambda kv: -kv[1])[:3])
import os
os.makedirs('site', exist_ok=True)
json.dump(dict(date=TARGET.isoformat(), generat=dt.date.today().isoformat(), grid=G, cells=cells, noms=NOM, boscos=NOMS_BOSC), open('site/cells.json', 'w'),
          ensure_ascii=False, separators=(',', ':'))
print(os.path.getsize('site/cells.json'))
