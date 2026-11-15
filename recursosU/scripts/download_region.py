import urllib.request,urllib.parse,json
from pathlib import Path
import numpy as np
f=json.loads(Path('data/raw/ez-layer4.json').read_text())['features'][0];pts=np.array(f['geometry']['rings'][0]);bbox=[*pts.min(0),*pts.max(0)]
base=json.loads(Path('docs/trek-config.json').read_text())['services']['globalDEMService']['equirect']
p=dict(bbox=','.join(map(str,bbox)),bboxSR=104905,imageSR=104905,size='512,512',format='tiff',pixelType='F32',interpolation='RSP_NearestNeighbor',noData=-32768,f='json',renderingRule=json.dumps({'rasterFunction':'None'}))
u=base+'/exportImage?'+urllib.parse.urlencode(p);d=json.load(urllib.request.urlopen(u,timeout=60));print(d);Path('docs/region-export.json').write_text(json.dumps({'request':u,'response':d},indent=2));urllib.request.urlretrieve(u.replace('f=json','f=image'),'data/raw/ez-mola.tif')
