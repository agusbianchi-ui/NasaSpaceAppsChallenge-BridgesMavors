"""Read-only inspection of the original, including a visual height grid (not a DEM)."""
from pathlib import Path
import struct,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output-stage1'
b=(ROOT/'MapaMarteN.glb').read_bytes(); length=struct.unpack_from('<I',b,12)[0]; j=json.loads(b[20:20+length]); binary=memoryview(b)[28+length:]
def array(i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']];dt={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]; n={'SCALAR':1,'VEC3':3,'VEC4':4,'VEC2':2}[a['type']]; offset=v.get('byteOffset',0)+a.get('byteOffset',0); stride=v.get('byteStride',np.dtype(dt).itemsize*n)
 return np.ndarray((a['count'],n),dtype=dt,buffer=binary,offset=offset,strides=(stride,np.dtype(dt).itemsize)).copy()
mins=[];maxs=[];triangles=0;tops=[]; normals={};blocks=[];degenerate=0; colors=[]
for m in j['meshes']:
 for p in m['primitives']:
  pos=array(p['attributes']['POSITION']);ix=array(p['indices']).reshape(-1,3);t=pos[ix]; cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);degenerate+=int(np.sum(np.all(cross==0,axis=1)));triangles+=len(ix);mins.append(pos.min(0));maxs.append(pos.max(0));colors.append(array(p['attributes']['COLOR_0']).shape)
  top=(np.ptp(t[:,:,1],axis=1)==0)&(cross[:,1]>0);tt=t[top];tops.append(np.column_stack((tt[:,:,0].min(1),tt[:,:,2].min(1),tt[:,0,1])));blocks.extend(np.unique(np.column_stack((np.ptp(tt[:,:,0],axis=1),np.ptp(tt[:,:,2],axis=1))),axis=0).tolist())
  for axis in range(3):normals[str(axis)]=normals.get(str(axis),0)+int(np.count_nonzero(cross[:,axis]))
lo=np.min(mins,axis=0);hi=np.max(maxs,axis=0);tops=np.concatenate(tops);unique=np.unique(tops,axis=0);step=250.;rows=int(round((hi[2]-lo[2])/step));cols=int(round((hi[0]-lo[0])/step));grid=np.full((rows,cols),np.nan,dtype='<f4');ri=np.rint((unique[:,1]-lo[2])/step).astype(int);ci=np.rint((unique[:,0]-lo[0])/step).astype(int);assert np.all((ri>=0)&(ri<rows)&(ci>=0)&(ci<cols));grid[ri,ci]=unique[:,2];valid=np.isfinite(grid)
# Flood-fill outside empty space; distinguish enclosed missing top cells from open exterior.
from collections import deque
seen=np.zeros_like(valid);q=deque()
for r,c in [(r,c) for r in range(rows) for c in (0,cols-1)]+[(r,c) for c in range(cols) for r in (0,rows-1)]:
 if not valid[r,c] and not seen[r,c]:seen[r,c]=1;q.append((r,c))
while q:
 r,c=q.popleft()
 for nr,nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
  if 0<=nr<rows and 0<=nc<cols and not valid[nr,nc] and not seen[nr,nc]:seen[nr,nc]=1;q.append((nr,nc))
grid.tofile(OUT/'visual-height.f32');valid.astype('u1').tofile(OUT/'visual-valid.u8')
report={'source_sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'MiB':len(b)/2**20,'triangles':triangles,'meshes':len(j['meshes']),'materials':len(j['materials']),'nodes':len(j['nodes']),'scenes':j['scenes'],'animations':len(j.get('animations',[])),'textures':len(j.get('textures',[])),'bounds':[lo.tolist(),hi.tolist()],'dimensions':(hi-lo).tolist(),'block_top_extent_unique':np.unique(blocks,axis=0).tolist(),'degenerate_triangles':degenerate,'cross_nonzero_per_axis':normals,'top_triangles':len(tops),'unique_top_cells':len(unique),'enclosed_empty_cells':int(np.sum(~valid&~seen)),'grid':{'shape':[rows,cols],'origin_xz':[float(lo[0]),float(lo[2])],'step':step,'order':'row increases +Z; column increases +X; centers origin+(index+0.5)*step','heights':'GLB local Y, float32 little-endian; visual, NOT scientific elevation','nodata':'NaN; valid.u8 1 present 0 absent'},'georeference_verified':False,'vertical_exaggeration':'scene name says 3x; no rescaling applied'}
(OUT/'geometry.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8');print(json.dumps(report,ensure_ascii=False))

# A vertical face is internal if both adjacent columns cover its entire Y range.
internal=0;vertical=0;downward=0
for mesh in j['meshes']:
 for p in mesh['primitives']:
  pos=array(p['attributes']['POSITION']);t=pos[array(p['indices']).reshape(-1,3)];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);downward+=int(np.sum(cross[:,1]<0))
  for axis in (0,2):
   faces=t[cross[:,axis]!=0];vertical+=len(faces);centers=faces.mean(1);heights=[]
   for sign in (-1,1):
    samples=centers.copy();samples[:,axis]+=sign*.1;rr=np.floor((samples[:,2]-lo[2])/step).astype(int);cc=np.floor((samples[:,0]-lo[0])/step).astype(int);inside=(rr>=0)&(rr<rows)&(cc>=0)&(cc<cols);h=np.full(len(rr),np.nan);h[inside]=grid[rr[inside],cc[inside]];heights.append(h)
   internal+=int(np.sum(faces[:,:,1].max(1)<=np.minimum(*heights)))
report['fully_internal_vertical_triangles']=internal;report['vertical_triangles']=vertical;report['downward_triangles']=downward
(OUT/'geometry.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print('Internal vertical faces:',internal,'downward:',downward)
