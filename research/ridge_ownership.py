"""Whole-curve baseline fallback for persistent competing-ridge ownership changes.

This guard certifies only centering risk: a final centered curve selects two
separate, simultaneously persistent CT/probability basins. It restores that
curve's original mature geometry; it creates no connection or split.
"""
import json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from bounded_logit_recenter import arclength,at_arc,frames,sample,validate_traces
from transverse_centering import center_scores

PARAMETERS = {
    'station_step_max_vox':1., 'symmetric_tangent_half_support_vox':4.,
    'context_radius_vox':8., 'grid_step_vox':.5, 'ownership_radius_vox':4.,
    'maximum_boundary_guard_vox':.5, 'peak_min_separation_vox':1.,
    'maximum_peaks_per_station':8, 'bright_peak_dog_z_min':0.,
    'match_transverse_max_vox':1., 'match_longitudinal_fraction':[.5,1.5],
    'mutual_match_second_distance_margin_vox':.5,
    'stable_owner_run_vox':8., 'simultaneous_competition_run_vox':8.,
    'competing_peak_separation_vox':2., 'both_tube_lifetimes_cover_transition_with_8vox_context':True, 'peak_saddle_prominence_energy':.5,
    'energy':'logit(Pfamily+Pintersection), clip1e-5, + CT_G1 transverse DoG/MAD; no radial prior',
    'decision':'restore entire original curve when final centers change persistent competing basins',
}
AXIS=np.arange(-8.,8.01,.5)
UU,VV=np.meshgrid(AXIS,AXIS,indexing='ij')
R2=UU*UU+VV*VV


def _owner(field,uv,indices):
    """Steepest ascent to a physical basin, with unresolved boundary/plateaus."""
    row,col=np.rint(np.asarray(uv)/.5+16).astype(int)
    if not (0<=row<33 and 0<=col<33 and np.isfinite(field[row,col])):return None
    for _ in range(64):
        lo,hi=max(0,row-1),min(33,row+2);left,right=max(0,col-1),min(33,col+2)
        block=field[lo:hi,left:right];dr,dc=np.unravel_index(np.argmax(block),block.shape)
        nr,nc=lo+dr,left+dc
        if field[nr,nc]<=field[row,col]+1e-6:break
        row,col=nr,nc
    distance=np.linalg.norm(indices-np.array([row,col]),axis=1)*.5
    j=int(np.argmin(distance)) if len(distance) else -1
    return j if j>=0 and distance[j]<.51 else None


def _runs(owners,arc):
    out=[];start=0
    for end in range(1,len(owners)+1):
        if end==len(owners) or owners[end]!=owners[start]:
            if owners[start] is not None and arc[end-1]-arc[start]>=8.-1e-6:
                out.append((owners[start],start,end-1))
            start=end
    return out


def curve_certificate(points,moved,ct1,family):
    original_arc=arclength(points);length=original_arc[-1]
    if length<16.:return {'certified':False,'reason':'fewer than two 8-voxel runs'}
    arc=np.linspace(0.,length,int(np.ceil(length))+1)
    q=at_arc(points,original_arc,arc);m=at_arc(moved,original_arc,arc)
    t=at_arc(points,original_arc,np.minimum(length,arc+4.))-at_arc(points,original_arc,np.maximum(0.,arc-4.))
    norms=np.linalg.norm(t,axis=1);assert np.all(norms>1e-10)
    t/=norms[:,None];u,v=frames(t)
    rows=[];size_xyz=np.asarray(ct1.shape[::-1],float);next_id=0
    for low in range(0,len(q),64):
        high=min(low+64,len(q));xyz=q[low:high,None,None]+u[low:high,None,None]*UU[None,...,None]+v[low:high,None,None]*VV[None,...,None]
        complete=((xyz>=0.)&(xyz<=size_xyz-1.)).all((1,2,3))
        cp=sample(ct1,xyz);fp=sample(family,xyz);_,evidence=center_scores(cp,fp)
        pp=np.clip(fp,1e-5,1.-1e-5);energy=np.log(pp)-np.log1p(-pp)+evidence['dog_z']
        energy=np.where(fp>=.5,energy,-np.inf)
        maxima=energy>=ndi.maximum_filter(energy,size=(1,3,3),mode='nearest')-1e-7
        maxima&=(R2<=3.5**2+1e-8)[None]
        maxima&=evidence['dog_z']>0.
        maxima&=np.isfinite(energy)
        for local,k in enumerate(range(low,high)):
            indices=np.argwhere(maxima[local]) if complete[local] else np.empty((0,2),int)
            ranked=sorted(indices.tolist(),key=lambda ij:(-float(energy[local][tuple(ij)]),float(R2[tuple(ij)]),ij))
            selected=[]
            for ij in ranked:
                if all(np.linalg.norm(np.asarray(ij)-a)*.5>=1. for a in selected):selected.append(ij)
                if len(selected)==8:break
            indices=np.asarray(selected,int).reshape(-1,2)
            uv=np.c_[UU[tuple(indices.T)],VV[tuple(indices.T)]] if len(indices) else np.empty((0,2))
            positions=q[k]+uv[:,:1]*u[k]+uv[:,1:]*v[k]
            ids=[None]*len(positions)
            if rows and len(positions) and len(rows[-1]['xyz']):
                previous=rows[-1];direction=t[k]+t[k-1];direction/=np.linalg.norm(direction)
                delta=positions[:,None]-previous['xyz'][None];along=delta@direction
                transverse=np.linalg.norm(delta-along[:,:,None]*direction,axis=2)
                step=arc[k]-arc[k-1]
                valid=(transverse<=1.)&(along>=.5*step)&(along<=1.5*step)
                cost=np.where(valid,transverse,np.inf)
                near_current=np.argmin(cost,axis=1);near_previous=np.argmin(cost,axis=0)
                for i,j in enumerate(near_current):
                    if not np.isfinite(cost[i,j]) or near_previous[j]!=i:continue
                    a=np.sort(cost[i]);b=np.sort(cost[:,j])
                    margin_a=a[1]-a[0] if len(a)>1 else np.inf
                    margin_b=b[1]-b[0] if len(b)>1 else np.inf
                    if margin_a>=.5 and margin_b>=.5:ids[i]=previous['ids'][j]
            for i in range(len(ids)):
                if ids[i] is None:ids[i]=next_id;next_id+=1
            working=np.where(R2<=16.+1e-8,energy[local],-np.inf)
            delta=m[k]-q[k];index=_owner(working,[float(delta@u[k]),float(delta@v[k])],indices)
            index0=_owner(working,[0.,0.],indices)
            rows.append({'xyz':positions,'ids':ids,'indices':indices,'energy':energy[local],
                         'owner':ids[index] if index is not None else None,
                         'baseline_owner':ids[index0] if index0 is not None else None})
    owners=[row['owner'] for row in rows];runs=_runs(owners,arc);certificates=[]
    for left,right in zip(runs,runs[1:]):
        a,lo,left_end=left;b,right_start,hi=right
        if a==b:continue
        # Tube tokens are never reused and a missing station creates a new token.
        # Require both tube lifetimes across transition plus 8 voxels either side.
        # A dying ridge followed by one continuing ridge stays unresolved.
        window_low=max(0,int(np.searchsorted(arc,arc[left_end]-8.,side='right'))-1)
        window_high=min(len(arc)-1,int(np.searchsorted(arc,arc[right_start]+8.,side='left')))
        if any(a not in rows[k]['ids'] or b not in rows[k]['ids'] for k in [window_low,window_high]):continue
        start=None;best=0.;interval=None
        for k in range(lo,hi+1):
            row=rows[k];ok=False
            if a in row['ids'] and b in row['ids']:
                i,j=row['ids'].index(a),row['ids'].index(b)
                if np.linalg.norm(row['xyz'][i]-row['xyz'][j])>=2.:
                    ij1,ij2=row['indices'][i],row['indices'][j]
                    line=np.rint(np.linspace(ij1,ij2,max(2,int(np.linalg.norm(ij1-ij2)*2)+1))).astype(int)
                    saddle=float(row['energy'][tuple(line.T)].min())
                    peaks=min(float(row['energy'][tuple(ij1)]),float(row['energy'][tuple(ij2)]))
                    ok=peaks-saddle>=.5
            if ok:
                if start is None:start=k
                if arc[k]-arc[start]>best:best=float(arc[k]-arc[start]);interval=[float(arc[start]),float(arc[k])]
            else:start=None
        if best>=8.-1e-6:
            certificates.append({'from_tube':int(a),'to_tube':int(b),
                'left_owner_arc_vox':[float(arc[lo]),float(arc[left_end])],
                'right_owner_arc_vox':[float(arc[right_start]),float(arc[hi])],
                'persistent_competition_arc_vox':interval,'persistent_competition_vox':best,
                'both_tube_lifetime_context_arc_vox':[float(arc[window_low]),float(arc[window_high])]})
    return {'certified':bool(certificates),'certificates':certificates,'stations':len(arc),
            'stable_centered_owner_runs':len(runs),
            'stable_original_owner_runs':len(_runs([r['baseline_owner']for r in rows],arc)),
            'ridge_tubes':next_id}


def guard(original,centered,probabilities,ct):
    """Inputs contain no annotations; original and centered IDs align exactly."""
    validate_traces(original,ct.shape);validate_traces(centered,ct.shape)
    if ct.dtype!=np.uint8 or probabilities.dtype!=np.float32 or probabilities.shape!=(4,)+ct.shape:
        raise ValueError('uint8 CT ZYX and float32 probabilities 4ZYX required')
    original_curves={str(c['id']):c for c in original['curves']}
    assert set(original_curves)=={str(c['id'])for c in centered['curves']}
    ct1=ndi.gaussian_filter(ct.astype(np.float32),1.,mode='nearest',truncate=4.)
    output=[];diagnostics=[]
    family_fields={'V':probabilities[1]+probabilities[3],'H':probabilities[2]+probabilities[3]}
    for curve in centered['curves']:
        c0=original_curves[str(curve['id'])];assert c0['family']==curve['family'] and c0.get('gaps',[])==curve.get('gaps',[])
        assert len(c0['points_xyz'])==len(curve['points_xyz'])
        fp=family_fields[curve['family']]
        result=curve_certificate(np.asarray(c0['points_xyz'],float),np.asarray(curve['points_xyz'],float),ct1,fp)
        diagnostics.append(dict(result,source_id=str(curve['id'])))
        output.append(dict(curve,points_xyz=c0['points_xyz']) if result['certified'] else curve)
    data=dict(centered,curves=output,stage='bounded-logit-ct-persistent-ownership',ownership_guard_parameters=PARAMETERS,
        restored_baseline_curve_ids=[d['source_id']for d in diagnostics if d['certified']],
        length_voxels=sum(float(arclength(np.asarray(c['points_xyz']))[-1])for c in output),
        labels_as_algorithm_input=False,topology_edits=0)
    return data,diagnostics


if __name__=='__main__':
    import argparse
    from bounded_logit_recenter import recenter
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ct',required=True);p.add_argument('--probabilities',required=True);p.add_argument('--traces',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();ct=np.load(a.ct,allow_pickle=False);prob=np.load(a.probabilities,mmap_mode='r',allow_pickle=False)
    original=json.loads(Path(a.traces).read_text());centered=recenter(original,prob,ct)
    data,_=guard(original,centered,prob,ct);Path(a.out).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
