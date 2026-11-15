import json,hashlib,struct
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import Window
from pyproj import Transformer
root=Path(__file__).resolve().parents[1];out=root/'output';out.mkdir(exist_ok=True)
src=root/'data/raw/M20_JezeroCrater_CTXDEM_20m.tif'
with rasterio.open(src) as s:
 w=Window(775,1987,768,768);a=s.read(1,window=w);mask=s.read_masks(1,window=w)>0;t=s.window_transform(w);crs=s.crs
 assert mask.all(), 'Selected region contains NoData; select or handle explicitly'
 profile=s.profile;profile.update(width=768,height=768,transform=t)
 with rasterio.open(out/'jezero-dem.tif','w',**profile) as d:d.write(a,1)
a.astype('<f4').tofile(out/'elevation.f32');mask.astype('uint8').tofile(out/'valid.u8')
x0=t.c+7680;y0=t.f-7680;z0=-4500.;base=float(np.floor(a.min()/100)*100-100)
ll=Transformer.from_crs(crs,crs.geodetic_crs,always_xy=True)
meta=dict(region='Jezero western delta sector',source='Mars 2020 Science Investigation CTX DEM Mosaic',mission='Mars Reconnaissance Orbiter',instrument='CTX',source_url='https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif',download_url='https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif',sha256=hashlib.sha256(src.read_bytes()).hexdigest(),crs_wkt=crs.to_wkt(),vertical_reference='Source elevation values preserved. PDS4 label does not specify vertical datum; do not mix with other DTMs until verified.',source_window=[775,1987,768,768],shape=[768,768],affine=list(t)[:6],origin_projected=[x0,y0,z0],axes='GLB X east, Y up, Z south',model_from_source='X=E-x0; Y=height-z0; Z=y0-N',scale=1,unit='metre',resolution_m=20,elevation_range_m=[float(a.min()),float(a.max())],geographic_corners_lon_lat=[ll.transform(*t*(c,r)) for c,r in [(0,0),(768,0),(768,768),(0,768)]],binary='elevation.f32 little-endian float32, row-major north to south; valid.u8 1 valid/0 NoData',quantization_m=2,quantization_error_bound_m=1,palette='Illustrative elevation-based ochre/brown; not measured surface color',base_m=base,processing=['crop only, no reprojection','LOD 20/40/80 m block means','nearest 2 m height quantization','exposed side faces only; common origin; no bottom mesh'],source_nodata=float(-3.4028234663852886e38))
(out/'metadata.json').write_text(json.dumps(meta,indent=2))
manifest=[];tests=[]
def glb(path,pos,norm,col,extras):
 pos=np.asarray(pos,dtype='<f4');norm=np.asarray(norm,dtype='<f4');col=np.asarray(col,dtype='<f4');n=len(pos);idx=np.arange(n,dtype='<u4').reshape(-1,4)[:,[0,1,2,0,2,3]].ravel();arrays=[pos,norm,col,idx];blob=b'';views=[]
 for ar in arrays:
  b=ar.tobytes();views.append(dict(buffer=0,byteOffset=len(blob),byteLength=len(b)));blob+=b
 access=[dict(bufferView=i,componentType=5126 if i<3 else 5125,count=len(ar),type='VEC3' if i<3 else 'SCALAR') for i,ar in enumerate(arrays)]
 access[0].update(min=pos.min(0).tolist(),max=pos.max(0).tolist())
 doc=dict(asset={'version':'2.0','generator':'Jezero scientific voxel pipeline'},scene=0,scenes=[{'nodes':[0]}],nodes=[{'mesh':0,'extras':extras}],meshes=[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'COLOR_0':2},'indices':3,'material':0}]}],materials=[{'name':'Mars matte illustrative','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'metallicFactor':0,'roughnessFactor':1}}],buffers=[{'byteLength':len(blob)}],bufferViews=views,accessors=access)
 j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);blob+=b'\0'*((-len(blob))%4)
 path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(j)+len(blob))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(blob),0x004e4942)+blob)
 return len(idx)//3
for lod,k in enumerate([1,2,4]):
 h=a.reshape(768//k,k,768//k,k).mean(axis=(1,3));q=np.round(h/2)*2;N=len(q);step=20*k
 expanded=np.repeat(np.repeat(q,k,0),k,1);err=expanded-a
 tests.append(dict(lod=lod,max_error_m=float(abs(err).max()),rmse_m=float(np.sqrt(np.mean(err**2)))))
 for rr in range(0,N,128):
  for cc in range(0,N,128):
   ps=[];ns=[];cs=[]
   def face(v,n,color):ps.extend(v);ns.extend([n]*4);cs.extend([color]*4)
   for r in range(rr,min(rr+128,N)):
    for c in range(cc,min(cc+128,N)):
     H=float(q[r,c]);Y=H-z0;X=t.c+c*step-x0;Z=y0-t.f+r*step
     f=float(np.clip((h[r,c]-a.min())/(a.max()-a.min()),0,1));color=(.19+.20*f,.105+.17*f,.065+.12*f)
     face([(X,Y,Z),(X,Y,Z+step),(X+step,Y,Z+step),(X+step,Y,Z)],(0,1,0),color)
     for dr,dc,n in [(-1,0,(0,0,-1)),(1,0,(0,0,1)),(0,-1,(-1,0,0)),(0,1,(1,0,0))]:
      nr,nc=r+dr,c+dc;other=float(q[nr,nc]) if 0<=nr<N and 0<=nc<N else base
      if other>=H:continue
      B=other-z0
      if dr==-1:v=[(X,B,Z),(X,Y,Z),(X+step,Y,Z),(X+step,B,Z)]
      elif dr==1:v=[(X+step,B,Z+step),(X+step,Y,Z+step),(X,Y,Z+step),(X,B,Z+step)]
      elif dc==-1:v=[(X,B,Z+step),(X,Y,Z+step),(X,Y,Z),(X,B,Z)]
      else:v=[(X+step,B,Z),(X+step,Y,Z),(X+step,Y,Z+step),(X+step,B,Z+step)]
      face(v,n,color)
   name=f'jezero_lod{lod}_{rr//128}_{cc//128}.glb';path=out/name
   tris=glb(path,ps,ns,cs,dict(source_sha256=meta['sha256'],lod=lod,origin=meta['origin_projected'],axes=meta['axes'],resolution_m=step))
   manifest.append(dict(file=name,lod=lod,resolution_m=step,row=rr,col=cc,rows=min(128,N-rr),cols=min(128,N-cc),triangles=tris,bytes=path.stat().st_size))
 print('LOD',lod,'done',flush=True)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
(out/'validation-data.json').write_text(json.dumps(dict(lod_errors=tests,valid_cells=int(mask.sum()),sample_checks=[dict(row=r,col=c,source_height=float(a[r,c]),model_height=float(round(float(a[r,c])/2)*2-z0),lon_lat=ll.transform(*t*(c+.5,r+.5))) for r,c in [(0,0),(300,300),(767,767),(100,600),(600,100)]],projection_note='Native equirectangular metres; scale varies with latitude, no vertical exaggeration; not a geodesic distance model.'),indent=2))
