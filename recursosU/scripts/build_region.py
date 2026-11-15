import json,hashlib,struct
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import Window
from pyproj import Transformer
root=Path(__file__).resolve().parents[1];out=root/'output-region';out.mkdir(exist_ok=True)
src=root/'data/raw/ez-mola.tif'
from rasterio.warp import reproject,Resampling
from rasterio.features import geometry_mask
from rasterio.transform import from_origin
from pyproj import CRS
with rasterio.open(src) as ds:
 crs=CRS.from_proj4('+proj=aeqd +lat_0=17.5 +lon_0=77 +a=3396190 +rf=169.894447223612 +units=m +no_defs')
 t=from_origin(-128000,128000,500,500);a=np.full((512,512),np.nan,dtype='float32')
 reproject(rasterio.band(ds,1),a,src_transform=ds.transform,src_crs=ds.crs,dst_transform=t,dst_crs=crs,src_nodata=ds.nodata,dst_nodata=np.nan,resampling=Resampling.nearest)
 f=json.loads((root/'data/raw/ez-layer4.json').read_text())['features'][0]
 tr=Transformer.from_crs(ds.crs,crs,always_xy=True)
 rings=[[tr.transform(*p) for p in ring] for ring in f['geometry']['rings']]
 mask=geometry_mask([{'type':'Polygon','coordinates':rings}],out_shape=a.shape,transform=t,invert=True)&np.isfinite(a)
 a[~mask]=np.nan
 profile=dict(driver='GTiff',width=512,height=512,count=1,dtype='float32',crs=crs,transform=t,nodata=np.nan)
 with rasterio.open(out/'ez-dem.tif','w',**profile) as d:d.write(a,1)
a.astype('<f4').tofile(out/'elevation.f32');mask.astype('uint8').tofile(out/'valid.u8')
x0=0.;y0=0.;z0=-4500.;base=float(np.floor(np.nanmin(a)/100)*100-100)
ll=Transformer.from_crs(crs,crs.geodetic_crs,always_xy=True)
meta=dict(region='Jezero Crater NASA EMC EZ Buffer FID 27, full 100 km radius',source='MOLA 128/64 merged DEM via NASA Mars Trek ImageServer',mission='Mars Global Surveyor',instrument='MOLA',source_url='https://planetarymaps.usgs.gov/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif',download_url='https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif',sha256=hashlib.sha256(src.read_bytes()).hexdigest(),crs_wkt=crs.to_wkt(),vertical_reference='Source elevation values preserved. PDS4 label does not specify vertical datum; do not mix with other DTMs until verified.',source_window=None,shape=[512,512],affine=list(t)[:6],origin_projected=[x0,y0,z0],axes='GLB X east, Y up, Z south',model_from_source='X=E-x0; Y=height-z0; Z=y0-N',scale=1,unit='metre',resolution_m=500,elevation_range_m=[float(np.nanmin(a)),float(np.nanmax(a))],geographic_corners_lon_lat=[ll.transform(*t*(c,r)) for c,r in [(0,0),(512,0),(512,512),(0,512)]],binary='elevation.f32 little-endian float32, row-major north to south; valid.u8 1 valid/0 NoData',quantization_m=2,quantization_error_bound_m=1,palette='Illustrative elevation-based ochre/brown; not measured surface color',base_m=base,processing=['nearest resampling to local azimuthal equidistant 500 m; official polygon mask','LOD 500/1000/2000 m valid block means; border coverage generalized at coarse LOD','nearest 2 m height quantization','exposed side faces only; common origin; no bottom mesh'],source_nodata=float(-3.4028234663852886e38))
meta.update(source_url=json.loads((root/'docs/region-export.json').read_text())['request'],download_url='NASA ImageServer exportImage f=image',vertical_reference='MOLA topography relative to areoid; exported numerical DEM, not shaded relief',source_resolution_degrees=0.00781224569558698,boundary_source='https://trek.nasa.gov/mars/trekarcgis/rest/services/EZMars/MapServer/4',boundary_fid=27,boundary_radius_km=100,region_center_lon_lat=[77,17.5])
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
 h=np.nanmean(a.reshape(512//k,k,512//k,k),axis=(1,3));q=np.round(h/2)*2;N=len(q);step=500*k
 expanded=np.repeat(np.repeat(q,k,0),k,1);err=expanded-a
 tests.append(dict(lod=lod,max_error_m=float(np.nanmax(abs(err))),rmse_m=float(np.sqrt(np.nanmean(err**2)))))
 for rr in range(0,N,128):
  for cc in range(0,N,128):
   ps=[];ns=[];cs=[]
   def face(v,n,color):ps.extend(v);ns.extend([n]*4);cs.extend([color]*4)
   for r in range(rr,min(rr+128,N)):
    for c in range(cc,min(cc+128,N)):
     if not np.isfinite(q[r,c]):continue
     H=float(q[r,c]);Y=H-z0;X=t.c+c*step-x0;Z=y0-t.f+r*step
     f=float(np.clip((h[r,c]-np.nanmin(a))/(np.nanmax(a)-np.nanmin(a)),0,1));color=(.19+.20*f,.105+.17*f,.065+.12*f)
     face([(X,Y,Z),(X,Y,Z+step),(X+step,Y,Z+step),(X+step,Y,Z)],(0,1,0),color)
     for dr,dc,n in [(-1,0,(0,0,-1)),(1,0,(0,0,1)),(0,-1,(-1,0,0)),(0,1,(1,0,0))]:
      nr,nc=r+dr,c+dc;other=float(q[nr,nc]) if 0<=nr<N and 0<=nc<N else base
      if not np.isfinite(other):other=base
      if other>=H:continue
      B=other-z0
      if dr==-1:v=[(X,B,Z),(X,Y,Z),(X+step,Y,Z),(X+step,B,Z)]
      elif dr==1:v=[(X+step,B,Z+step),(X+step,Y,Z+step),(X,Y,Z+step),(X,B,Z+step)]
      elif dc==-1:v=[(X,B,Z+step),(X,Y,Z+step),(X,Y,Z),(X,B,Z)]
      else:v=[(X+step,B,Z),(X+step,Y,Z),(X+step,Y,Z+step),(X+step,B,Z+step)]
      face(v,n,color)
   if not ps:continue
   name=f'ez_lod{lod}_{rr//128}_{cc//128}.glb';path=out/name
   tris=glb(path,ps,ns,cs,dict(source_sha256=meta['sha256'],lod=lod,origin=meta['origin_projected'],axes=meta['axes'],resolution_m=step))
   manifest.append(dict(file=name,lod=lod,resolution_m=step,row=rr,col=cc,rows=min(128,N-rr),cols=min(128,N-cc),triangles=tris,bytes=path.stat().st_size))
 print('LOD',lod,'done',flush=True)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
(out/'validation-data.json').write_text(json.dumps(dict(lod_errors=tests,valid_cells=int(mask.sum()),sample_checks=[dict(row=r,col=c,source_height=float(a[r,c]),model_height=float(round(float(a[r,c])/2)*2-z0),lon_lat=ll.transform(*t*(c+.5,r+.5))) for r,c in [(256,256),(180,180),(330,330),(150,300),(300,150)]],projection_note='Azimuthal equidistant, central distance preserved; off-center distortion remains. Cell-center boundary rasterization up to cell half diagonal.'),indent=2))
