from pathlib import Path
import cv2,urllib.request
cap=cv2.VideoCapture(r'C:\Users\agusb\Videos\Captures\DEATH STRANDING 2_ ON THE BEACH v1.0.48.0 2026-11-14 10-56-21.mp4')
n=cap.get(cv2.CAP_PROP_FRAME_COUNT);fps=cap.get(cv2.CAP_PROP_FPS);print('video',n,fps,n/fps)
frames=[]
for f in [.15,.5,.85]:
 cap.set(cv2.CAP_PROP_POS_FRAMES,int(n*f));ok,im=cap.read()
 if ok: frames.append(cv2.resize(im,(640,360)))
cv2.imwrite('docs/video-reference.jpg',cv2.hconcat(frames))
u='https://asc-pds-services.s3.us-west-2.amazonaws.com/mosaic/mars2020_trn/CTX/ScienceInvestigationMaps_JPL/M20_JezeroCrater_CTXDEM_20m.xml'
urllib.request.urlretrieve(u,'data/raw/M20_JezeroCrater_CTXDEM_20m.xml')
