"""Executable checks for the published experimental primitives."""
from pathlib import Path
import importlib.util
import numpy as np
from incoming_tangent_probe import trace, reverse_consistent

spec=importlib.util.spec_from_file_location('centering',Path(__file__).with_name('transverse_centering.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
u,v=np.meshgrid(np.arange(-8.,8.01,.5),np.arange(-8.,8.01,.5),indexing='ij')
r2=u*u+v*v
scores,evidence=c.center_scores(100+50*np.exp(-r2/2),.95*np.exp(-r2/32))
shift,available=c.choose_center(scores['family_gated_bright_prior'],radius_vox=1.5)
assert available and np.array_equal(shift,[0.,0.])
assert not c.choose_center(c.center_scores(100+50*np.exp(-r2/2),np.zeros_like(r2))[0]['family_gated_bright_prior'])[1]
z,y,x=np.indices((48,48,80))
ct=(100+90*np.exp(-((y-24.)**2+(z-24.)**2)/3.)).astype(np.uint8)
p=np.zeros((4,)+ct.shape,np.float32);p[1]=np.exp(-((y-24.)**2+(z-24.)**2)/16.);p[0]=1-p[1]
curves=[{'id':0,'family':'V','points_xyz':[[20.,24.,24.],[50.,24.,24.]],'gaps':[]}]
outputs,e=trace(curves,p,ct)
assert len(outputs)==1 and len(outputs[0]['points_xyz'])>20
kept,a=reverse_consistent(outputs,p,ct)
assert len(kept)==1 and a['curves'][0]['bidirectional_fraction_min']==1.
print('centering gate, incoming flow and reverse consistency checks passed')
