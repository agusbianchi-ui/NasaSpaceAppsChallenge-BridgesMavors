"""Validate downloaded originals, native masks and three real queries; write evidence only."""
from pathlib import Path
import hashlib, json, runpy, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'WebApp/backend'))
PACK = ROOT / 'data/additional-science/BridgesMavors_science_pack'
helpers = runpy.run_path(str(PACK / 'prepare_science.py'))
catalog = json.loads((PACK / 'science_catalog.json').read_text(encoding='utf8'))
records = []
for dataset, folder in [(catalog['datasets'][0], 'thermal'), (catalog['datasets'][1], 'roughness')]:
    for item in dataset['files']:
        path = PACK / 'raw' / folder / item['name']
        data = path.read_bytes()
        if 'md5' in item:
            assert hashlib.md5(data).hexdigest() == item['md5']
        records.append({'file': str(path.relative_to(ROOT)), 'url': item['url'],
                        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
for period in ['day', 'night']:
    for mask in [False, True]:
        stem = f'global_ti_{"msk_" if mask else ""}{period}_2007'
        helpers['validate_label'](PACK/'raw/thermal'/f'{stem}.lbl', period, mask)
        assert (PACK/'raw/thermal'/f'{stem}.img').stat().st_size == 3600*7200*(1 if mask else 2)

from app.services.terrain_science import TerrainScienceService
from app.services.tes_thermal import ROOT as TES_ROOT
import numpy as np
service = TerrainScienceService()
samples = []
for x,z in [(24875,-55625),(8375,-20625),(-50000,0)]:
    point = service.point(x,z)
    for period in ['day','night']:
        datum = point['variables'][f'thermal_inertia_{period}']
        cell = datum['sample']['cell']; r,c = cell['row'],cell['column']
        raw = np.memmap(TES_ROOT/'raw/thermal'/f'global_ti_{period}_2007.img',dtype='>i2',mode='r',shape=(3600,7200))
        quality = np.memmap(TES_ROOT/'raw/thermal'/f'global_ti_msk_{period}_2007.img',dtype='i1',mode='r',shape=(3600,7200))
        assert datum['value'] == int(raw[r,c]) and quality[r,c] != 0
    samples.append(point)
out = ROOT/'docs/additional-science'
(out/'download-integrity.json').write_text(json.dumps(records,indent=2),encoding='utf8')
(out/'three-samples.json').write_text(json.dumps(samples,indent=2),encoding='utf8')
print('Verified 18 original files, four labels, sizes, author MD5 and six raw/GeoTIFF samples.')
