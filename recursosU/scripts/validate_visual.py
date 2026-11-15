import json,struct,numpy as np,rasterio
from pathlib import Path
r=Path('output-visual');meta=json.loads((r/'metadata.json').read_text());a=np.fromfile(r/'elevation.f32',dtype='<f4').reshape(1024,1024);m=json.loads((r/'manifest.json').read_text());n=0;maxerror=0.
for item in m:
 if item['lod']!=0:continue
 b=(r/item['file']).read_bytes();jl=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+jl]);start=28+jl
 def attr(i):
  ac=j['accessors'][i];v=j['bufferViews'][ac['bufferView']];return np.frombuffer(b,dtype='<f4',count=ac['count']*3,offset=start+v.get('byteOffset',0)).reshape(-1,3)
 p=attr(0);normal=attr(1);top=p[normal[:,1]>.9].reshape(-1,4,3);center=top.mean(1);row=np.rint((center[:,2]+128000)/250-.5).astype(int);col=np.rint((center[:,0]+128000)/250-.5).astype(int)
 expected=(np.round(a[row,col]/2)*2+4500)*3
 assert np.isfinite(expected).all();error=np.abs(center[:,1]-expected);maxerror=max(maxerror,float(error.max()));n+=len(top)
 assert np.allclose(np.diff(top[:,:,0],axis=1)[:,1],250)
 assert np.isfinite(p).all()
assert n==np.isfinite(a).sum();assert maxerror<.01
report=dict(all_lod0_columns_checked=n,max_export_height_error_m=maxerror,vertical_exaggeration=3,inverse='height = GLB.Y/3 - 4500',quantization_error_source_m=1,quantization_error_display_m=3)
(r/'validation-scientific.json').write_text(json.dumps(report,indent=2));print(report)
