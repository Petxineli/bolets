import json, os, re
S='site/'
h=open(S+'index.html').read()
def rd(p): return open(S+p).read()
# inline leaflet
h=re.sub(r'/\*FOCCTL\*/.*?/\*END\*/','',h)
# base maps + locate + opacity
old="  const g=d.grid;"
new="""  const topo=L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',{maxZoom:17,subdomains:'abc',attribution:'© OpenTopoMap, © OpenStreetMap'});
  const osm=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'});
  const sat=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:18,attribution:'Esri World Imagery'});
  L.control.layers({'Sense fons':base,'Topogràfic (camins i relleu)':topo,'Satèl·lit':sat},(fireLayer?{'🔥 Zones cremades 2025-2026 (aprox.)':fireLayer}:{}),{collapsed:false,position:'topright'}).addTo(map);
  map.on('baselayerchange',e=>{ baseOn = e.layer!==base; if(!baseOn) base.bringToBack(); polys.forEach(({p,lay})=>{ if(lay!==selPoly) lay.setStyle(stylePoly(p)); }); zoomMode(); });
  const op=L.control({position:'topright'}); op.onAdd=()=>{ const d=L.DomUtil.create('div','opbox'); d.innerHTML='<label>Transparència dels boscos<input type="range" min="10" max="85" value="35"></label>'; L.DomEvent.disableClickPropagation(d);
    d.querySelector('input').oninput=e=>{ polyOp=e.target.value/100; polys.forEach(({p,lay})=>{ if(lay!==selPoly) lay.setStyle(stylePoly(p)); }); }; return d; }; op.addTo(map);
  const loc=L.control({position:'topleft'}); loc.onAdd=()=>{ const b=L.DomUtil.create('button','locbtn'); b.type='button'; b.textContent='📍 On sóc'; L.DomEvent.disableClickPropagation(b); b.onclick=()=>map.locate({setView:true,maxZoom:14,enableHighAccuracy:true}); return b; }; loc.addTo(map);
  let me; map.on('locationfound',e=>{ if(me) me.remove(); me=L.circleMarker(e.latlng,{radius:7,color:'#fff',weight:2,fillColor:'#1a73e8',fillOpacity:1}).addTo(map); });
  map.on('locationerror',()=>{ document.getElementById('mode').textContent='No he pogut obtenir la ubicació. Revisa el permís del navegador.'; });
  const g=d.grid;"""
assert old in h; h=h.replace(old,new,1)
h=h.replace("col?0.85:0.25}","col?(baseOn?polyOp:0.85):(baseOn?0.04:0.25)}")
h=h.replace("(z?0.12:0.82)","(z?0.12:(baseOn?0.55:0.82))")
h=h.replace("active = 'total';","active = 'total', baseOn = false, polyOp = 0.35;")
h=h.replace("</style>",".locbtn{font:600 12px 'IBM Plex Sans',sans-serif;padding:6px 10px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--ink);cursor:pointer}.opbox{background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:6px 10px;font:12px 'IBM Plex Sans',sans-serif}.opbox input{display:block;width:150px;margin-top:4px}.leaflet-control-layers{font:12px 'IBM Plex Sans',sans-serif}\n</style>",1)
import shutil
W='out/web/'
shutil.rmtree(W,ignore_errors=True)
shutil.copytree(S,W,ignore=shutil.ignore_patterns('index.html'))
open(W+'index.html','w').write(h)
print(len(h)/1e6,'MB')
