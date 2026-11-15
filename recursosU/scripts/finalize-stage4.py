"""Inventory generated stage 4 artifacts after processing; never touches source models."""
from pathlib import Path
import hashlib
import json
from importlib.metadata import version

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output-stage4'
metadata = json.loads((OUT / 'terrain_metadata.json').read_text(encoding='utf8'))
files = []
for path in sorted(OUT.iterdir()):
    if path.is_file() and path.name != 'manifest.json':
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        files.append({'file': path.name, 'bytes': path.stat().st_size, 'sha256': digest})
manifest = {'original': '../MapaMarteN.glb', 'source_sha256': metadata['source_sha256'],
            'no_new_3d_model': True, 'files': files,
            'processing_versions': {name: version(name) for name in ['numpy', 'rasterio', 'pyproj', 'netCDF4']}}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
print(f'Inventoried {len(files)} stage 4 files.')
