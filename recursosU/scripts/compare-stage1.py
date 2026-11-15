"""Reproducible image comparison and delivery inventory; run after Blender renders."""
from pathlib import Path
import json,hashlib,cv2,numpy as np
OUT=Path(__file__).resolve().parents[1]/'output-stage1'
metrics={};rows=[]
for view in ['overview','detail']:
 a=cv2.imread(str(OUT/f'original-{view}.png'));b=cv2.imread(str(OUT/f'optimized-{view}.png'));assert a.shape==b.shape;d=np.abs(a.astype('i2')-b.astype('i2'));metrics[view]={'max_channel_difference_8bit':int(d.max()),'mean_absolute_channel_difference':float(d.mean()),'different_pixel_fraction':float(np.any(d,axis=2).mean())};rows.append(np.concatenate([a,b],axis=1))
cv2.imwrite(str(OUT/'comparison.png'),np.concatenate(rows,axis=0));(OUT/'visual-comparison.json').write_text(json.dumps(metrics,indent=2))
files=[]
for p in sorted(OUT.rglob('*')):
 if p.is_file() and p.suffix in ['.glb','.f32','.u8','.png']:
  with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
  files.append({'file':p.relative_to(OUT).as_posix(),'bytes':p.stat().st_size,'sha256':h})
(OUT/'inventory.json').write_text(json.dumps(files,indent=2))
