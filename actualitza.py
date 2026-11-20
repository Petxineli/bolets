"""Actualitza tot el mapa: baixa dades del Meteocat, recalcula i construeix out/web/.
Ús: python3 actualitza.py [YYYY-MM-DD de la sortida]
Per defecte: sortida = avui si són abans de les 12:00 (hora de Catalunya), si no demà."""
import subprocess, sys, os, shutil, glob, datetime as dt
from zoneinfo import ZoneInfo

# Prepara l'estructura de carpetes a partir dels fitxers del directori principal
for d in ('data', 'site/lib'):
    os.makedirs(d, exist_ok=True)
with open('data/boscos-catalunya.json', 'wb') as out:
    for p in sorted(glob.glob('boscos-*.txt')):
        out.write(open(p, 'rb').read())
for src, dst in (('cells.txt', 'data/cells.txt'), ('estacions.json', 'data/estacions.json'),
                 ('index.html', 'site/index.html'), ('guia.html', 'site/guia.html'), ('comarques.json', 'site/comarques.json'),
                 ('leaflet.js', 'site/lib/leaflet.js'), ('leaflet.css', 'site/lib/leaflet.css')):
    shutil.copy(src, dst)

now = dt.datetime.now(ZoneInfo('Europe/Madrid'))
today = now.date()
target = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else (today if now.hour < 12 else today + dt.timedelta(1))
run = lambda *a: subprocess.run([sys.executable, *a], check=True)
run('download_meteo.py', today.isoformat())
run('meteo.py', 'data', target.isoformat(), today.isoformat())
run('score.py', target.isoformat())
run('-I', 'poly.py', target.isoformat())
run('build_web.py')
print('OK: dades fins a', today, '· previsió per a', target)
