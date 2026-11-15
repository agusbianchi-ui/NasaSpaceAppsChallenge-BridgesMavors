import urllib.request
u='https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.tif'
with urllib.request.urlopen(u,timeout=60) as r:
 print(r.status,dict(r.headers),flush=True)
 with open('data/raw/M20_JezeroCrater_CTXDEM_20m.tif','wb') as f:
  while b:=r.read(1024*1024): f.write(b)
print('download complete')

