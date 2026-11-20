"""Calcula indicadors meteorològics per estació XEMA a partir de les dades diàries descarregades."""
import json, collections, datetime as dt, sys

D = sys.argv[1] if len(sys.argv) > 1 else 'data'
TODAY = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date.today()
TARGET = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else TODAY + dt.timedelta(1)
SEASON = dt.date(TODAY.year if TODAY.month >= 9 else TODAY.year - 1, 9, 1)  # inici de la temporada


def load(f):
    out = collections.defaultdict(dict)
    for r in json.load(open(f'{D}/{f}')):
        out[r['codi_estacio']][dt.date.fromisoformat(r['dia'][:10])] = float(r['v'])
    return out


st = {s['codi_estacio']: s for s in json.load(open(f'{D}/estacions.json'))}
P, TX, TN, W = load('pluja.json'), load('tmax.json'), load('tmin.json'), load('ratxa.json')


def pulse_weight(age):
    """Pes d'una pluja segons els dies que fa respecte al dia de sortida.
    Els bolets solen sortir entre 5 i 12 dies després d'una pluja forta."""
    if age < 2: return 0.0
    if age < 5: return (age - 2) / 3
    if age <= 12: return 1.0
    if age <= 20: return (20 - age) / 8
    return 0.0


res = {}
for c, s in st.items():
    p = P.get(c)
    if not p or len(p) < min(60, (TODAY - SEASON).days * 0.8):
        continue
    last7 = [TODAY - dt.timedelta(d) for d in range(7)]
    rec = {
        'nom': s['nom_estacio'], 'lat': float(s['latitud']), 'lon': float(s['longitud']),
        'alt': float(s['altitud']), 'comarca': s['nom_comarca'],
        'p_set_oct': round(sum(v for d, v in p.items() if SEASON <= d <= SEASON.replace(month=10, day=20)), 1),
        'p30': round(sum(v for d, v in p.items() if TODAY - dt.timedelta(29) <= d <= TODAY), 1),
        'p_pols': round(sum(v * pulse_weight((TARGET - d).days) for d, v in p.items()), 1),
    }
    # pluja més important dels darrers 20 dies (per a l'explicació)
    big = max(((v, d) for d, v in p.items() if (TODAY - d).days <= 20), default=(0, None))
    # suma per episodis de dos dies consecutius
    best = (0, None)
    for d in sorted(p):
        if (TODAY - d).days > 20: continue
        v2 = p[d] + p.get(d + dt.timedelta(1), 0)
        if v2 > best[0]: best = (v2, d)
    rec['episodi_mm'] = round(best[0], 1)
    rec['episodi_dia'] = best[1].isoformat() if best[1] else None
    tn = [TN[c][d] for d in last7 if d in TN.get(c, {})]
    tx = [TX[c][d] for d in last7 if d in TX.get(c, {})]
    if tn and tx:
        rec['tn7'] = round(sum(tn) / len(tn), 1)
        rec['tx7'] = round(sum(tx) / len(tx), 1)
        rec['tnmin7'] = min(tn)
        rec['gelades7'] = sum(v < 0 for v in tn)
    w = [W[c][d] for d in last7 if d in W.get(c, {})]
    if w:
        rec['dies_vent7'] = sum(v >= 15 for v in w)  # ratxa >= 54 km/h
        rec['ratxa_max7'] = max(w)
    res[c] = rec

json.dump(res, open(f'{D}/meteo_estacions.json', 'w'), ensure_ascii=False, indent=0)
print(len(res), 'estacions')
for c in ['CI', 'DG', 'CY', 'W5', 'X4', 'CQ']:
    if c in res: print(c, res[c])
