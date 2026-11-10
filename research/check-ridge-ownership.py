import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
from ridge_ownership import curve_certificate,guard
from scipy import ndimage as ndi
shape=(64,64,64);z,y,x=np.indices(shape)
ct=np.clip(70+100*np.exp(-((y-29)**2+(z-32)**2)/2.)+100*np.exp(-((y-35)**2+(z-32)**2)/2.),0,255).astype(np.uint8)
prob=np.zeros((4,)+shape,np.float32);prob[0]=.005;prob[2]=.995
points=np.c_[np.arange(10.,51.),np.full(41,32.),np.full(41,32.)]
moved=points.copy();moved[:20,1]-=1.25;moved[20:,1]+=1.25
ct1=ndi.gaussian_filter(ct.astype(np.float32),1.,mode='nearest',truncate=4.)
a=curve_certificate(points,moved,ct1,prob[2]);assert a['certified'],a
assert curve_certificate(points[::-1],moved[::-1],ct1,prob[2])['certified']
base={'coordinates':'ROI-local XYZ voxels','shape_zyx':list(shape),'curves':[{'id':'pair','family':'H','gaps':[],'points_xyz':points.tolist()}]}
centred=dict(base,curves=[dict(base['curves'][0],points_xyz=moved.tolist())])
result,_=guard(base,centred,prob,ct);assert result['curves'][0]['points_xyz']==points.tolist()
single=np.clip(70+100*np.exp(-((y-29)**2+(z-32)**2)/2.),0,255).astype(np.uint8)
r=curve_certificate(points,moved,ndi.gaussian_filter(single.astype(np.float32),1.,mode='nearest'),prob[2]);assert not r['certified'],r
result,_=guard(base,centred,prob,single);assert result['curves'][0]['points_xyz']==moved.tolist()
# One owner throughout a two-ridge field is retained; weak/flat CT provides no certificate.
same=moved.copy();same[:,1]=30.75
assert not curve_certificate(points,same,ct1,prob[2])['certified']
assert not curve_certificate(points,moved,np.full(shape,70.,np.float32),prob[2])['certified']
dying=np.clip(70+100*np.exp(-((y-29)**2+(z-32)**2)/2.)*(x<29)+100*np.exp(-((y-35)**2+(z-32)**2)/2.),0,255).astype(np.uint8)
assert not curve_certificate(points,moved,ndi.gaussian_filter(dying.astype(np.float32),1.,mode='nearest'),prob[2])['certified']
print('PASS: two persistent separated owners restore exact baseline; single owner/peak/weak CT retained; ID/gaps unchanged')
