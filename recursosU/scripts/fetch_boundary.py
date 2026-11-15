import urllib.request,urllib.parse,json
from pathlib import Path
Path('data/raw').mkdir(parents=True,exist_ok=True)
base='https://trek.nasa.gov/mars/trekarcgis/rest/services/EZMars/MapServer/4'
u=base+'/query?'+urllib.parse.urlencode(dict(where='FID=27',outFields='*',returnGeometry='true',f='json'))
d=json.load(urllib.request.urlopen(u,timeout=60));assert d['features'][0]['attributes']['name']=='Jezero Crater'
Path('data/raw/ez-layer4.json').write_text(json.dumps(d))
u='https://trek.nasa.gov/mars/jpl/config/config.json'
Path('docs').mkdir(exist_ok=True)
Path('docs/trek-config.json').write_bytes(urllib.request.urlopen(u).read())
