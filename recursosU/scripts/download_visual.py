import rasterio, numpy as np, urllib.request, cv2, json, hashlib
from pathlib import Path
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
from concurrent.futures import ThreadPoolExecutor
u='https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/Mars/HRSC_MOLA_Blend/Mars_HRSC_MOLA_BlendDEM_Global_200mp_v2.tif'
import io,tifffile,math
head=urllib.request.urlopen(urllib.request.Request(u,headers={'Range':'bytes=0-1048575'}),timeout=50).read()
tf=tifffile.TiffFile(io.BytesIO(head));page=tf.pages[0]
assert tf.byteorder=='<' and page.compression==1 and page.dtype==np.dtype('int16')
with rasterio.io.MemoryFile(head) as mem:
 with mem.open() as ds:
  w=from_bounds(75,15.4,79,19.5,ds.transform).round_offsets().round_lengths();p=ds.profile;p.update(width=int(w.width),height=int(w.height),transform=ds.window_transform(w))
r0=int(w.row_off);r1=r0+int(w.height);begin=page.dataoffsets[r0];end=page.dataoffsets[r1-1]+page.databytecounts[r1-1]
def fetch_span(span):
 lo,hi=span
 return urllib.request.urlopen(urllib.request.Request(u,headers={'Range':f'bytes={lo}-{hi-1}'}),timeout=60).read()
parts=[(i,min(i+16*1024*1024,end)) for i in range(begin,end,16*1024*1024)]
with ThreadPoolExecutor(max_workers=6) as pool:raw=b''.join(pool.map(fetch_span,parts))
assert len(raw)==end-begin
full=np.frombuffer(raw,dtype='<i2').reshape(int(w.height),page.shape[1]);a=full[:,int(w.col_off):int(w.col_off+w.width)].copy()
with rasterio.open('data/raw/ez-hrsc200.tif','w',**p) as d:d.write(a,1)
print('HRSC downloaded',a.shape,flush=True)
# WMTS geographic matrix per published capabilities: 256 columns,128 rows at level7.
tile=180/128;cols=range(int((75+180)//tile),int((79+180)//tile)+1);rows=range(int((90-19.5)//tile),int((90-15.4)//tile)+1)
canvas=np.zeros((len(rows)*256,len(cols)*256,3),dtype=np.uint8);records=[]
def get(rc):
 r,c=rc;url=f'https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/default/default028mm/7/{r}/{c}.jpg';b=urllib.request.urlopen(url,timeout=40).read();im=cv2.imdecode(np.frombuffer(b,np.uint8),1)[:,:,::-1];return r,c,im,dict(url=url,sha256=hashlib.sha256(b).hexdigest())
with ThreadPoolExecutor(max_workers=4) as pool:
 for r,c,im,rec in pool.map(get,[(r,c) for r in rows for c in cols]):canvas[(r-rows.start)*256:(r-rows.start+1)*256,(c-cols.start)*256:(c-cols.start+1)*256]=im;records.append(rec)
with rasterio.open('data/raw/ez-viking.tif','w',driver='GTiff',width=canvas.shape[1],height=canvas.shape[0],count=3,dtype='uint8',crs='+proj=longlat +R=3396190 +no_defs',transform=from_origin(-180+cols.start*tile,90-rows.start*tile,tile/256,tile/256)) as d:d.write(canvas.transpose(2,0,1))
Path('docs/visual-sources.json').write_text(json.dumps(dict(dem=u,color=records),indent=2));print('Viking color downloaded',canvas.shape)
