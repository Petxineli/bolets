"""Descarrega dades diàries XEMA (Meteocat, Socrata) i les desa a data/. Ús: python3 download_meteo.py YYYY-MM-DD (data final inclosa)"""
import json, sys, urllib.parse, urllib.request, datetime as dt
END = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
_e = dt.date.fromisoformat(END)
SEASON = dt.date(_e.year if _e.month >= 9 else _e.year - 1, 9, 1).isoformat()  # inici de la temporada (1 de setembre)
D30 = (_e - dt.timedelta(30)).isoformat()
B = 'https://analisi.transparenciacatalunya.cat/resource/nzvn-apee.json'
def q(var, agg, start, out):
    rows, off = [], 0
    while True:
        p = {'$select': f"codi_estacio,date_trunc_ymd(data_lectura) as dia,{agg}(valor_lectura::number) as v",
             '$where': f"codi_variable='{var}' AND data_lectura>='{start}T00:00:00' AND data_lectura<'{END}T23:59:59'",
             '$group': 'codi_estacio,dia', '$order': 'codi_estacio,dia', '$limit': '50000', '$offset': str(off)}
        u = B + '?' + urllib.parse.urlencode(p)
        r = json.load(urllib.request.urlopen(u, timeout=180))
        rows += r
        if len(r) < 50000: break
        off += 50000
    json.dump(rows, open(f'data/{out}.json', 'w'))
    print(out, len(rows), 'files; última data', max(x['dia'] for x in rows)[:10])
q('35', 'sum', SEASON, 'pluja')
q('40', 'max', D30, 'tmax')
q('42', 'min', D30, 'tmin')
q('50', 'max', D30, 'ratxa')
