#!/usr/bin/env python3
"""Reference-free physical transverse centering primitive.

Input CT patches sample an isotropic Gaussian-sigma1 CT volume in an
incoming-tangent-orthogonal frame. Probability patches use fixed float
P(own family class)+P(intersection). Both inputs have shape (N,H,W) or (H,W).
An odd 33x33 patch, 0.5 voxel grid, covers radius8. The original physical
voxel spacing is 7.91 um. This module receives no graph, labels, or manual IDs.
"""
import numpy as np
from scipy import ndimage as ndi


def center_scores(ct_patch, family_patch, *, grid_step_vox=.5,
                  background_sigma_vox=2., prior_sigma_vox=2.):
    """Return named score maps and evidence maps with the input spatial shape.

    Recommended candidate use is a small incoming continuation disk.
    CT ridge = CT_G1 - G_perp_sigma2(CT_G1); ridge / local_MAD + log(Pf+I).
    local_MAD uses radius6, scale = max(1.4826 * MAD(ridge), 1 CT gray level).
    The probability gate is Pf+I >= .5. The prior score subtracts |u|^2/8.
    """
    ct=np.asarray(ct_patch,dtype=np.float32)
    p=np.asarray(family_patch,dtype=np.float32)
    assert ct.shape==p.shape and ct.ndim in (2,3)
    single=ct.ndim==2
    if single:ct=ct[None];p=p[None]
    h,w=ct.shape[-2:];assert h%2==1 and w%2==1
    ux=(np.arange(h,dtype=np.float32)-h//2)*grid_step_vox
    vx=(np.arange(w,dtype=np.float32)-w//2)*grid_step_vox
    uu,vv=np.meshgrid(ux,vx,indexing='ij');rr2=uu*uu+vv*vv
    mad_disk=rr2<=36.+1e-6
    background=ndi.gaussian_filter(ct,sigma=(0,background_sigma_vox/grid_step_vox,background_sigma_vox/grid_step_vox),mode='nearest',truncate=2.)
    ridge=ct-background
    median=np.median(ridge[:,mad_disk],axis=1)
    scale=np.maximum(1.4826*np.median(np.abs(ridge[:,mad_disk]-median[:,None]),axis=1),1.)
    z=ridge/scale[:,None,None]
    logp=np.log(np.clip(p,1e-4,1.))
    # Axiswise transverse derivatives keep independent patches separate.
    dx,dy=np.gradient(ct,grid_step_vox,axis=(1,2),edge_order=2)
    hxx=np.gradient(dx,grid_step_vox,axis=1,edge_order=2)
    hyy=np.gradient(dy,grid_step_vox,axis=2,edge_order=2)
    hxy=(np.gradient(dx,grid_step_vox,axis=2,edge_order=2)+np.gradient(dy,grid_step_vox,axis=1,edge_order=2))*.5
    tr=(hxx+hyy)*.5
    disc=np.sqrt(np.maximum((hxx-hyy)**2*.25+hxy*hxy,0.))
    lam_big,lam_small=tr+disc,tr-disc
    tube=np.maximum(-lam_big,0.)/scale[:,None,None]
    gated=np.where(p>=.5,z+logp,-np.inf)
    scores={'probability_peak':logp,'bright_ct':z,'dark_ct':-z,
            'family_gated_bright':gated,
            'family_gated_bright_prior':gated-rr2[None]/(2*prior_sigma_vox**2),
            'family_gated_tube':np.where(p>=.5,tube+logp,-np.inf)}
    evidence={'dog':ridge,'dog_z':z,'mad':scale,
              'bright_tube_eigen_max':lam_big,'bright_tube_eigen_min':lam_small}
    if single:
        scores={key:value[0] for key,value in scores.items()}
        evidence={key:value[0] for key,value in evidence.items()}
    return scores,evidence


def choose_center(score, *, grid_step_vox=.5, radius_vox=1.5):
    """Choose one bounded offset; nearest incoming point wins exact-score ties.

    Returns (offset_uv_vox, evidence_available). A fully gated-out patch gives
    zero offset and False. Continuous tracer stopping can consume that flag.
    """
    score=np.asarray(score)
    assert score.ndim in (2,3)
    single=score.ndim==2
    if single:score=score[None]
    h,w=score.shape[-2:]
    u=(np.arange(h,dtype=np.float32)-h//2)*grid_step_vox
    v=(np.arange(w,dtype=np.float32)-w//2)*grid_step_vox
    uu,vv=np.meshgrid(u,v,indexing='ij');rr2=uu*uu+vv*vv
    bounded=np.where(rr2[None]<=radius_vox**2+1e-6,score,-np.inf)
    available=np.isfinite(bounded).any((1,2))
    index=np.argmax((bounded-1e-8*rr2[None]).reshape(len(score),-1),axis=1)
    offsets=np.stack([uu.ravel()[index],vv.ravel()[index]],axis=1)
    offsets[~available]=0.
    return (offsets[0],bool(available[0])) if single else (offsets,available)
