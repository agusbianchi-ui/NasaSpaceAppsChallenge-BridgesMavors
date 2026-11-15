"""Extract visual column tops from scene-space triangles; never infer scientific elevations."""
from pathlib import Path
import json,struct,hashlib
import numpy as np
from collections import deque
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output-stage3';OUT.mkdir(exist_ok=True)
b=(ROOT/'MapaMarteN.glb').read_bytes();n=struct.unpack_from('<I',b,12)[0];j=json.loads(b[20:20+n]);blob=memoryview(b)[28+n:]
def accessor(i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];dt={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']];size={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
 return np.ndarray((a['count'],size),dtype=dt,buffer=blob,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',np.dtype(dt).itemsize*size),np.dtype(dt).itemsize)).copy()
def local(node):
 if 'matrix' in node:return np.array(node['matrix']).reshape(4,4,order='F')
 x,y,z,w=node.get('rotation',[0,0,0,1]);r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
 m=np.eye(4);m[:3,:3]=r@np.diag(node.get('scale',[1,1,1]));m[:3,3]=node.get('translation',[0,0,0]);return m
records=[];transforms=[];bounds=[];extents=[]
def visit(idx,parent):
 node=j['nodes'][idx];world=parent@local(node)
 if 'mesh' in node:
  transforms.append({'node':idx,'matrix':world.T.flatten().tolist()})
  for p in j['meshes'][node['mesh']]['primitives']:
   assert p.get('mode',4)==4
   v=accessor(p['attributes']['POSITION']);v=(np.c_[v,np.ones(len(v))]@world.T)[:,:3];t=v[accessor(p['indices']).reshape(-1,3)];bounds.append([v.min(0),v.max(0)])
   normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);top=t[(np.ptp(t[:,:,1],axis=1)<1e-6)&(normal[:,1]>0)]
   extents.append(np.column_stack([np.ptp(top[:,:,0],axis=1),np.ptp(top[:,:,2],axis=1)]));records.append(np.column_stack([top[:,:,0].min(1),top[:,:,2].min(1),top[:,0,1]]))
 for child in node.get('children',[]):visit(child,world)
for idx in j['scenes'][j.get('scene',0)]['nodes']:visit(idx,np.eye(4))
limits=np.array(bounds);lo=limits[:,0].min(0);hi=limits[:,1].max(0);sizes=np.unique(np.concatenate(extents),axis=0);assert sizes.shape==(1,2) and sizes[0,0]==sizes[0,1];step=float(sizes[0,0]);tops=np.unique(np.concatenate(records),axis=0)
rows=int(round((hi[2]-lo[2])/step));cols=int(round((hi[0]-lo[0])/step));grid=np.full((rows,cols),np.nan,dtype='<f4');rr=(tops[:,1]-lo[2])/step;cc=(tops[:,0]-lo[0])/step;assert np.allclose(rr,np.rint(rr)) and np.allclose(cc,np.rint(cc));rr=np.rint(rr).astype(int);cc=np.rint(cc).astype(int);assert len(np.unique(rr*cols+cc))==len(tops),'Multiple upper surfaces in a column';grid[rr,cc]=tops[:,2];valid=np.isfinite(grid)
# Flood exterior absence using four-neighbor connectivity; enclosed absent cells are holes.
exterior=np.zeros_like(valid);queue=deque()
for row in range(rows):
 for col in (0,cols-1):
  if not valid[row,col] and not exterior[row,col]:exterior[row,col]=True;queue.append((row,col))
for col in range(cols):
 for row in (0,rows-1):
  if not valid[row,col] and not exterior[row,col]:exterior[row,col]=True;queue.append((row,col))
while queue:
 row,col=queue.popleft()
 for r,c in ((row-1,col),(row+1,col),(row,col-1),(row,col+1)):
  if 0<=r<rows and 0<=c<cols and not valid[r,c] and not exterior[r,c]:exterior[r,c]=True;queue.append((r,c))
grid.tofile(OUT/'visual_elevation.bin');valid.astype('u1').tofile(OUT/'valid_mask.bin')
meta={'source':'MapaMarteN.glb','source_sha256':hashlib.sha256(b).hexdigest(),'rows':rows,'columns':cols,'cellSize':step,'originX':float(lo[0]),'originZ':float(lo[2]),'bounds':[lo.tolist(),hi.tolist()],'axes':'X local horizontal, Y up, Z local horizontal','order':'row-major: rows increase +Z, columns increase +X','cellConvention':'half-open [min,max), center=min+cellSize/2','dtype':'float32','endianness':'little','nodata':'NaN and mask=0','mask':'uint8, 1 valid, 0 absent','classification':'derived visual geometry; not scientific DEM','georeference_verified':False,'verticalScale':'retained; no division by 3','modelToOptimized':np.eye(4).flatten().tolist(),'nodeTransforms':transforms,'validCells':int(valid.sum())}
meta['enclosedHoleCells']=int((~valid & ~exterior).sum());meta['exteriorAbsentCells']=int(exterior.sum())
for name in ['visual_elevation.bin','valid_mask.bin']:meta[name]={'bytes':(OUT/name).stat().st_size,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
(OUT/'terrain_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf8')
r=json.loads((ROOT/'ruta_marte_preliminar.json').read_text());errors=[]
for point in r['points']:
 row=int(np.floor((point['z']-lo[2])/step));col=int(np.floor((point['x']-lo[0])/step));assert 0<=row<rows and 0<=col<cols and valid[row,col];errors.append(abs(float(grid[row,col])-point['y']))
check={'points':len(r['points']),'start':r['points'][0],'destination':r['points'][-1],'max_visual_y_difference':max(errors),'all_positions_valid':True,'optimized_transform':'identity','screenshot_alignment':'not required by user clarification: cyan circle and point only indicate preliminary start/end; no geographic registration claimed','route_status':r.get('status')}
(OUT/'preliminary-check.json').write_text(json.dumps(check,indent=2),encoding='utf8');print(json.dumps(check))
