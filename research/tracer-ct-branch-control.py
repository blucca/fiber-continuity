#!/usr/bin/env python3
"""Continue the fixed artificial contact probe with one CT-only basin control.

Linux / Python 3.12, in the same NumPy/SciPy/Numba environment as the parent:
  python3 research/tracer-ct-branch-control.py --author-source /path/to/AVF_SPLINE_GENERATOR \
    --scene-dir temp/sheet-contact-probe --output-dir temp/ct-branch-control
Add --check to assert saved control outputs without rerunning tracing.
The exact Apache-2.0 author tracer is imported from its external checkout;
this diagnostic adapter retains its source and original unmasked-P validator.
"""
import argparse,copy,datetime,hashlib,json,os,resource,runpy,subprocess,sys,time
from pathlib import Path
PARENT=runpy.run_path(str(Path(__file__).with_name('tracer-sheet-contact-probe.py')))
PIN=PARENT['PIN']; EXPECTED=PARENT['EXPECTED']; SCENE_PLAN=PARENT['PLAN']
OUT=SCENE=SOURCE=PLAN=None
CONTROL_SPEC=json.loads(r'''{
  "control": "one CT-derived planar normal-Z branch control on the existing artificial scene",
  "inputs": {
    "artificial-native-ct.npy": {
      "path": "scene-dir/artificial-native-ct.npy",
      "sha256": "50fb557e0b4b0d8e0e6aa80e575807ad5b24655c93ec8a87711f3a4345f64e99"
    },
    "native-predictions.npy": {
      "path": "scene-dir/native-predictions.npy",
      "sha256": "dd75e8b7edceae907a0e7fbe81025d93547be3c316e365ad75f42fc7b92634d8"
    }
  },
  "CT_algorithm_inputs": [
    "artificial-native-ct.npy only; full native XYZ domain; fixed normal Z; profile mean across all native Y at each native X"
  ],
  "CT_fixed_detection": {
    "find_peaks_prominence": 12,
    "find_peaks_distance": 2,
    "plateau_size": [
      1,
      null
    ],
    "required_supported_peaks_per_X": 2,
    "carrier_coordinate": "peak plateau edge midpoint",
    "valley": "minimum CT between the two peak plateaus; minimum plateau midpoint",
    "basin_assignment": "lower branch z <= valley; upper branch z > valley"
  },
  "probability_adapter": "mask original V by CT basin; retain original H exactly at 8/255",
  "seed_rule": "prepared primary only, x tracing 8..12/y9..11; nearest x10/y10 and interpolated corresponding CT peak; ties descending centrality; absent => STOP",
  "tail_probe_rule": "lower-branch actual prepared primary near x52/y10 and CT peak; diagnostic only, no extra trace",
  "branch_execution_order": [
    "upper_CT_branch",
    "lower_CT_branch"
  ],
  "coverage": "separate unchanged core count/direction arrays per CT branch; upper trace leaves lower coverage untouched",
  "core_parameters": {
    "min_raw_len": 7.5,
    "step_size": 0.75,
    "max_low_steps": 3,
    "core_r": 2.05
  },
  "finish": "original exactbee finish on branch inputs, then independently original unmasked pooled/native family gate on every raw/finished segment",
  "score_oracle": "fixed parent PLAN float32 A/B centrelines reconstructed only after all control traces and finish; nearest-reference normal-Z exact ties unknown",
  "comparators": "saved initial_raw and correct_zero_coverage whole curves; saved initial_finished for stage-matched fitted companion",
  "length_gate": "one complete raw and finished curve per branch; longest arc >=95% of both saved unconstrained whole raw curves; finished also compared to saved initial_finished",
  "resource_caps": {
    "seconds": 120,
    "RSS_MiB": 512,
    "threads": 1
  },
  "scenario_changes": 0,
  "configuration_searches": 0,
  "author_source_changes": 0,
  "scenario_control_runs": 1,
  "real_operator_frequency": "awaits actual V2 materials"
}''')

def make_plan():
 p=copy.deepcopy(CONTROL_SPEC)
 p.update(created_utc=now(),source_pin=PIN,expected_source_sha256=EXPECTED)
 return p

def score_oracle():
 # Called only after both CT-guided branches are traced and finished.
 # Float32 matches the saved original reference point-for-point.
 import numpy as np
 x=np.arange(SCENE_PLAN['tracing_shape_zyx'][2],dtype='f4')
 a=SCENE_PLAN['physical_A_z_tracing']; s=SCENE_PLAN['physical_B_separation_tracing']
 def mix(x,a,b,lo,hi):
  u=np.clip((x-lo)/(hi-lo),0,1)
  return a+(b-a)*(.5-.5*np.cos(np.pi*u))
 lo,near=s['cosine_transition_16_to_32']; near2,hi=s['cosine_transition_32_to_48']
 separation=np.where(x<=32,mix(x,lo,near,16,32),mix(x,near2,hi,32,48))
 return np.array([np.column_stack((x,np.full_like(x,10),np.full_like(x,a))),np.column_stack((x,np.full_like(x,10),a+separation))])

def validate_scene():
 import numpy as np
 if hashes()!=EXPECTED: raise Stop('exact external source hash mismatch')
 saved=json.loads((SCENE/'plan.json').read_text())
 for k in ['source_pin','native_shape_zyx','tracing_shape_zyx','physical_A_z_tracing','physical_B_separation_tracing','H_constant_u8','core_parameters']:
  if saved[k]!=SCENE_PLAN[k]: raise Stop('fixed parent scene PLAN mismatch: '+k)
 baseline=json.loads((SCENE/'summary.json').read_text())
 if baseline['status']!='complete' or baseline['source_pin']!=PIN: raise Stop('parent scene completion/PIN mismatch')
 if baseline['source_sha256_before']!=EXPECTED or baseline['source_sha256_after']!=EXPECTED: raise Stop('parent source hash mismatch')
 for name in ['artificial-native-ct.npy','native-predictions.npy','work/tracing.npy','curves.npz']:
  if not (SCENE/name).is_file(): raise Stop('parent artifact absent: '+name)
 for name,meta in PLAN['inputs'].items():
  if hashlib.sha256((SCENE/name).read_bytes()).hexdigest()!=meta['sha256']: raise Stop('fixed parent input hash mismatch: '+name)
 ct=np.load(SCENE/'artificial-native-ct.npy',mmap_mode='r',allow_pickle=False)
 p=np.load(SCENE/'native-predictions.npy',mmap_mode='r',allow_pickle=False)
 if ct.shape!=(40,40,128) or p.shape!=(2,40,40,128): raise Stop('fixed parent shape mismatch')
 if not np.array_equal(p[1],np.full_like(p[1],8/255)): raise Stop('original H contract mismatch')

def check_outputs():
 import numpy as np
 r=json.loads((OUT/'report.json').read_text())
 assert r['status']=='complete' and r['decision']=='PASS' and r['gates']['all_gates']
 assert r['source_sha256_before']==r['source_sha256_after']==EXPECTED==hashes()
 assert r['worker_seconds']<=120 and r['peak_RSS_kib']<=512*1024
 total=0
 with np.load(OUT/'curves-and-labels.npz',allow_pickle=False) as z:
  for b in r['branches']:
   for stage in ['raw','finished']:
    prefix=b['CT_branch']+'_'+stage
    da=z[prefix+'_distance_A_tracing']; db=z[prefix+'_distance_B_tracing']
    labels=np.where(da==db,-1,np.where(da<db,0,1)).astype('i1')
    assert np.array_equal(labels,z[prefix+'_physical_label_code'])
    assert np.all(labels==b['physical_score_target'])
    valid=z[prefix+'_curve0_original_P_valid_segments']; assert np.all(valid)
    total+=len(valid)
    own=da if b['physical_score_target']==0 else db
    assert b[stage]['maximum_normal_deviation_to_target_native_vox']==float(2*np.max(own))
 assert total==322
 save('assert-check.json',{'status':'passed','checked_utc':now(),'source_pin':PIN,'all_original_P_valid_segments':total,'checks':'saved complete output; exact source; exact-tie nearest-reference labels; per-stage native deviations; saved time/RSS caps','new_trace_calls':0})
 print('ASSERT PASSED',total,'original-P segments')
 return 0
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def hashes(): return {n:hashlib.sha256((SOURCE/'avf_spline_generator'/n).read_bytes()).hexdigest() for n in PLAN['expected_source_sha256']}
class Stop(Exception): pass

def worker():
 start=time.monotonic(); report={'status':'running','started_utc':now(),'plan':'plan.json','branches':[],'source_sha256_before':hashes()}
 try:
  import numpy as np,scipy,numba
  from scipy.signal import find_peaks
  sys.path.insert(0,str(SOURCE))
  from avf_spline_generator import core,prepare,tracing,storage
  if report['source_sha256_before']!=PLAN['expected_source_sha256']: raise Stop('source hash mismatch')
  for n,m in PLAN['inputs'].items():
   if hashlib.sha256((SCENE/n).read_bytes()).hexdigest()!=m['sha256']: raise Stop('input hash mismatch: '+n)
  ct=np.load(SCENE/'artificial-native-ct.npy',allow_pickle=False)
  original=np.load(SCENE/'native-predictions.npy',allow_pickle=False)
  if ct.shape!=(40,40,128) or original.shape!=(2,40,40,128): raise Stop('input shape mismatch')
  if not np.array_equal(original[1],np.full_like(original[1],8/255)): raise Stop('original H contract mismatch')
  profiles=ct.mean(axis=1,dtype='f8'); peaks=np.empty((2,ct.shape[2]),'f8'); valleys=np.empty(ct.shape[2],'f8'); evidence=[]
  for x in range(ct.shape[2]):
   p,props=find_peaks(profiles[:,x],prominence=12,distance=2,plateau_size=(1,None))
   if len(p)!=2:
    report['CT_failure']={'native_x':x,'detected_peaks':p.tolist(),'prominences':props['prominences'].tolist()}
    raise Stop('CT peak identification failed')
   left=props['left_edges']; right=props['right_edges']; peaks[:,x]=(left+right)/2
   lo=int(right[0])+1; hi=int(left[1])
   if hi<=lo: raise Stop('CT valley interval empty at x='+str(x))
   values=profiles[lo:hi,x]; inds=np.flatnonzero(values==values.min()); valley=lo+(int(inds[0])+int(inds[-1]))/2
   valleys[x]=valley
   evidence.append({'native_x':x,'peak_indices':p.tolist(),'plateau_edges':list(zip(left.tolist(),right.tolist())),'carrier_z_native':peaks[:,x].tolist(),'peak_prominences':props['prominences'].tolist(),'valley_z_native':float(valley),'valley_CT':float(values.min())})
  save('ct-evidence.json',{'algorithm_input':'original CT only','normal':'Z','profile':'mean over complete native Y','columns':evidence})
  np.savez_compressed(OUT/'ct-derived-fields.npz',profiles=profiles,carrier_peaks_z_native=peaks,valley_z_native=valleys)
  report['CT_detection']={'columns':len(evidence),'supported_peaks_each_column':2,'minimum_prominence':float(min(min(e['peak_prominences']) for e in evidence)),'CT_algorithm_oracle_inputs':0}
  orig_native=storage.Predictions(SCENE/'native-predictions.npy',order='VH')
  orig_sampler=storage.NativeSampler(orig_native,cache_mib=8,chunk=64)
  orig_pooled=np.load(SCENE/'work/tracing.npy',mmap_mode='r',allow_pickle=False)
  report['original_family_gate_inputs']={'native':'scene-dir/native-predictions.npy','pooled':'scene-dir/work/tracing.npy','pooled_sha256':hashlib.sha256((SCENE/'work/tracing.npy').read_bytes()).hexdigest(),'pooled_origin':'saved exact prepare_tracing result of original unmasked P','tolerance':1e-4,'maximum_tracing_step':0.25}
  branches=[]; arrays={}
  def select(branch,targetx):
   coords=np.asarray(branch['coords']); primary=branch['seeds'][tuple(coords.T)]==2
   eligible=primary & (coords[:,2]>=targetx-2)&(coords[:,2]<=targetx+2)&(coords[:,1]>=9)&(coords[:,1]<=11)
   ids=np.flatnonzero(eligible)
   if not len(ids): raise Stop('actual prepared primary absent for '+branch['name']+' x'+str(targetx))
   cs=coords[ids]; targetz=(np.interp(2*cs[:,2]+.5,np.arange(ct.shape[2]),peaks[branch['index']])-.5)/2
   dist=(cs[:,2]-targetx)**2+(cs[:,1]-10)**2+(cs[:,0]-targetz)**2
   ordering=np.lexsort((-branch['cent'][tuple(cs.T)].astype('i8'),dist)); q=cs[ordering[0]].astype('i4')
   return q,{'zyx_tracing':q.tolist(),'xyz_tracing':q[::-1].tolist(),'xyz_native':(2*q[::-1]+.5).tolist(),'generated_primary':bool(branch['seeds'][tuple(q)]==2),'seed_flag':int(branch['seeds'][tuple(q)]),'presence_u8':int(branch['presence'][tuple(q)]),'centrality_u16':int(branch['cent'][tuple(q)]),'eligible_primary_candidates':int(len(ids))}
  for index,name in enumerate(['lower_CT_branch','upper_CT_branch']):
   folder=OUT/name; folder.mkdir(exist_ok=True)
   basin=np.arange(ct.shape[0])[:,None,None]<=valleys[None,None,:]
   if index: basin=~basin
   masked=original.copy(); masked[0]*=basin
   np.save(folder/'native-predictions.npy',masked)
   np.save(folder/'ct-basin.npy',np.broadcast_to(basin,ct.shape))
   native=storage.Predictions(folder/'native-predictions.npy',order='VH'); work=folder/'work'; work.mkdir(exist_ok=True)
   pooled=prepare.prepare_tracing(native,None,work); axes=prepare.prepare_axes(pooled,work)
   presence,cent,seeds=prepare.prepare_family(pooled,axes,1,work/'family-1','cpu')
   coords,catalog=prepare.prepare_seeds(cent,seeds,work/'family-1')
   branch={'index':index,'name':name,'pooled':pooled,'axes':axes,'presence':presence,'cent':cent,'seeds':seeds,'coords':coords,'catalog':catalog,'sampler':storage.NativeSampler(native,cache_mib=8,chunk=64),'cov':[np.zeros(presence.shape,'u1') for _ in range(3)]}
   q,meta=select(branch,10); branch['seed']=q; branch['seed_meta']=meta; branches.append(branch)
  tail,tailmeta=select(branches[0],52)
  def probe(branch,q):
   z,y,x=map(int,q); u=core.decode_dir(branch['axes'][0][z,y,x],branch['axes'][1][z,y,x])
   return {'count':int(branch['cov'][0][z,y,x]),'direction_bytes':[int(branch['cov'][1][z,y,x]),int(branch['cov'][2][z,y,x])],'is_covered_same_dir':bool(core.is_covered_same_dir(*branch['cov'],x,y,z,*u))}
  before=probe(branches[0],tail)
  for index in [1,0]:
   b=branches[index]; pts=np.empty((2048,3),'f4'); tans=np.empty_like(pts); offsets=np.zeros(129,'i8')
   z,y,x=(np.array([i],dtype='i4') for i in b['seed'])
   n,k=core.trace_seed_range(b['cent'],b['presence'],*b['axes'],z,y,x,*b['cov'],pts,tans,offsets,0,0,0,1,n_pass1=1,**PLAN['core_parameters'])
   raw=pts[:n].copy(); rawt=tans[:n].copy(); rawo=offsets[:k+1].copy()
   finished,fo=tracing.finish(raw,rawo,b['pooled'],b['presence'],1,b['sampler'])
   b.update(raw=raw,rawt=rawt,rawo=rawo,finished=finished,fo=fo)
   if index==1:
    report['branch_aware_coverage']={'lower_tail_actual_seed':tailmeta,'lower_state_before_upper_trace':before,'lower_state_after_upper_trace':probe(branches[0],tail),'upper_coverage_at_lower_tail_without_branch_filter':probe(branches[1],tail)}
  report['branch_aware_coverage']['lower_state_after_own_lower_trace']=probe(branches[0],tail)
  # Algorithm complete. Oracle is first read below, solely for saved point labels and score.
  oracle=score_oracle()
  np.save(OUT/'score-oracle-tracing-xyz.npy',oracle)
  baseline=json.loads((SCENE/'summary.json').read_text())
  report['score_oracle']={'input':'score-oracle-tracing-xyz.npy','construction':'fixed parent PLAN, float32; score-only after all control trace/finish calls','used_after_all_control_traces_and_finish':True,'used_in_CT_algorithm':False,'assignment':'nearest normal-Z physical centre at each tracing X; exact distance ties unknown','label_codes':{'A':0,'B':1,'unknown':-1}}
  report['comparators']={k:baseline[k] for k in ['initial_raw','initial_finished','correct_seed_zero_coverage_raw']}
  allpass=True
  def stats(b,points,off,stage,target):
   cur=[]; invalid=0; seg=0; length=0.; switches=0; unknown=0; opposite=0; longest=0.
   az=np.interp(points[:,0],oracle[0,:,0],oracle[0,:,2]); bz=np.interp(points[:,0],oracle[1,:,0],oracle[1,:,2])
   da=np.abs(points[:,2]-az); db=np.abs(points[:,2]-bz); labels=np.where(da==db,-1,np.where(da<db,0,1)).astype('i1')
   prefix=b['name']+'_'+stage
   arrays[prefix+'_points_tracing_xyz']=points; arrays[prefix+'_points_native_xyz']=2*points.astype('f8')+.5; arrays[prefix+'_offsets']=off
   arrays[prefix+'_physical_label_code']=labels; arrays[prefix+'_distance_A_tracing']=da; arrays[prefix+'_distance_B_tracing']=db
   for a,z in zip(off[:-1],off[1:]):
    p=points[a:z]; lab=labels[a:z]; lens=np.linalg.norm(np.diff(p,axis=0),axis=1); arc=float(lens.sum(dtype='f8'))
    valid=tracing.valid_segments(p,orig_pooled,1,orig_sampler); bad=int((~valid).sum()); seg+=len(valid); invalid+=bad; length+=arc; longest=max(longest,arc)
    events=[{'global_segment':int(a+i),'from':int(lab[i]),'to':int(lab[i+1]),'xyz_before':p[i].tolist(),'xyz_after':p[i+1].tolist()} for i in np.flatnonzero(lab[1:]!=lab[:-1])]
    switches+=len(events); un=int((lab==-1).sum()); op=int(((lab>=0)&(lab!=target)).sum()); unknown+=un; opposite+=op
    cur.append({'points':len(p),'arc_tracing_vox':arc,'arc_native_vox':2*arc,'start_xyz_tracing':p[0].tolist(),'end_xyz_tracing':p[-1].tolist(),'start_physical_label':int(lab[0]),'end_physical_label':int(lab[-1]),'layer_events':events,'unknown_points':un,'opposite_layer_points':op,'all_segments':len(valid),'original_P_invalid_segments':bad})
    arrays[prefix+'_curve'+str(len(cur)-1)+'_original_P_valid_segments']=valid
   comparisons={k:{'arc_ratio':length/baseline[k]['arc_tracing_vox'] if baseline[k]['arc_tracing_vox'] else None,'longest_curve_ratio':longest/baseline[k]['longest_curve_arc_tracing_vox'] if baseline[k]['longest_curve_arc_tracing_vox'] else None,'delta_native_vox':2*(length-baseline[k]['arc_tracing_vox'])} for k in report['comparators']}
   return {'maximum_normal_deviation_to_target_native_vox':float(2*np.max(da if target==0 else db)) if len(points) else None,'curve_count':len(cur),'points':len(points),'all_segments':seg,'original_P_invalid_segments':invalid,'arc_tracing_vox':length,'arc_native_vox':2*length,'longest_curve_arc_tracing_vox':longest,'layer_event_count':switches,'unknown_points':unknown,'opposite_layer_points':opposite,'split_count':max(0,len(cur)-1),'length_comparisons':comparisons,'curves':cur}
  for b in branches:
   q=b['seed'][::-1]; d=[abs(q[2]-np.interp(q[0],oracle[i,:,0],oracle[i,:,2])) for i in [0,1]]; target=int(np.argmin(d))
   raw=stats(b,b['raw'],b['rawo'],'raw',target); fitted=stats(b,b['finished'],b['fo'],'finished',target)
   retain=all(s['length_comparisons'][k]['longest_curve_ratio'] is not None and s['length_comparisons'][k]['longest_curve_ratio']>=.95 for s in [raw,fitted] for k in ['initial_raw','correct_seed_zero_coverage_raw'])
   passed=retain and all(s['curve_count']==1 and s['original_P_invalid_segments']==s['layer_event_count']==s['unknown_points']==s['opposite_layer_points']==0 for s in [raw,fitted])
   allpass &= passed
   arrays[b['name']+'_raw_tangents']=b['rawt']
   report['branches'].append({'CT_branch':b['name'],'physical_score_target':target,'prepared_seed_catalog':b['catalog'],'prepared_start_seed':b['seed_meta'],'raw':raw,'finished':fitted,'long_chain_retention_gate':bool(retain),'branch_gate':bool(passed),'H_preserved_exact':True})
  coverage=report['branch_aware_coverage']; isolated=coverage['lower_state_before_upper_trace']['count']==coverage['lower_state_after_upper_trace']['count']==0
  report['gates']={'CT_two_supported_carriers_all_columns':True,'all_raw_finished_original_P_family_valid':all(s['original_P_invalid_segments']==0 for b in report['branches'] for s in [b['raw'],b['finished']]),'all_branches_no_physical_switch_unknown_or_opposite_points':all(s['layer_event_count']==s['unknown_points']==s['opposite_layer_points']==0 for b in report['branches'] for s in [b['raw'],b['finished']]),'both_branches_longest_whole_curve_95pct_retained':all(b['long_chain_retention_gate'] for b in report['branches']),'branch_coverage_isolated':isolated,'all_gates':bool(allpass and isolated)}
  np.savez_compressed(OUT/'curves-and-labels.npz',**arrays)
  report['normal_deviation_definition']='absolute normal-Z distance to own A/B reference interpolated at tracing X, multiplied by 2 for native voxels'
  report['combined_control_attribution']={'measured_combination':['CT-basin masking of original V','branch-specific prepared fields','independent unchanged coverage arrays'],'coverage_only_increment':'requires a separate actual-method control'}
  report['status']='complete'; report['decision']='PASS' if report['gates']['all_gates'] else 'STOP_FIXED_CONTROL_FAIL'
 except Exception as exc:
  report['status']='failed'; report['decision']='STOP_FIXED_CONTROL_FAIL'; report['failure_reason']=type(exc).__name__+': '+str(exc)
  if not isinstance(exc,Stop):
   import traceback; report['traceback']=traceback.format_exc()
 finally:
  report.update(finished_utc=now(),worker_seconds=time.monotonic()-start,peak_RSS_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,source_sha256_after=hashes(),configuration_searches=0,scenario_changes=0,source_changes=0)
  save('report.json',report)
  print(json.dumps({'status':report['status'],'decision':report['decision'],'worker_seconds':report['worker_seconds'],'failure_reason':report.get('failure_reason')},ensure_ascii=False))
 return 0 if report['status']=='complete' else 1

def supervise():
 save('plan.json',PLAN)
 save('source-refs.json',{'source_pin':PIN,'sha256':hashes(),'urls':{n:f'https://github.com/Qualzz/AVF_SPLINE_GENERATOR/blob/{PIN}/src/avf_spline_generator/{n}' for n in EXPECTED}})
 start=time.monotonic(); peak=0; reason=None
 env=dict(os.environ,NUMBA_NUM_THREADS='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBA_CACHE_DIR=str(OUT/'jit-cache'),PYTHONDONTWRITEBYTECODE='1')
 with (OUT/'run.stdout').open('w') as out,(OUT/'run.stderr').open('w') as err:
  child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker','--author-source',str(SOURCE),'--scene-dir',str(SCENE),'--output-dir',str(OUT)],env=env,stdout=out,stderr=err)
  while child.poll() is None:
   try:
    status=Path('/proc/'+str(child.pid)+'/status').read_text(); rss=int(next(line.split()[1] for line in status.splitlines() if line.startswith('VmRSS:'))); peak=max(peak,rss)
   except (FileNotFoundError,StopIteration): pass
   if peak>512*1024: reason='RSS cap exceeded'; break
   if time.monotonic()-start>120: reason='120 second cap exceeded'; break
   time.sleep(.05)
  if reason:
   child.terminate()
   try: child.wait(timeout=2)
   except subprocess.TimeoutExpired: child.kill(); child.wait()
 save('run-result.json',{'exit_code':child.returncode,'supervisor_seconds':time.monotonic()-start,'observed_peak_RSS_kib':peak,'resource_stop_reason':reason})
 if reason or child.returncode:
  if not (OUT/'report.json').exists(): save('report.json',{'status':'failed','decision':'STOP_FIXED_CONTROL_FAIL','failure_reason':reason or 'worker exit '+str(child.returncode),'source_sha256_after':hashes()})
  return child.returncode or 1
 r=json.loads((OUT/'report.json').read_text())
 assert r['source_sha256_before']==r['source_sha256_after']==PLAN['expected_source_sha256'] and r['status']=='complete' and r['worker_seconds']<=120 and peak<=512*1024
 save('assert-check.json',{'status':'passed','checked_utc':now(),'checks':'exact source unchanged; complete report; single-worker time/RSS caps','decision':r['decision']})
 return 0

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--author-source',type=Path,required=True,help='Existing exact bee798f7 author checkout root or src directory; source remains external.')
 parser.add_argument('--scene-dir',type=Path,required=True,help='Completed parent probe artifact directory, e.g. temp/sheet-contact-probe.')
 parser.add_argument('--output-dir',type=Path,required=True,help='Control artifact directory, e.g. temp/ct-branch-control; all generated files stay here.')
 parser.add_argument('--check',action='store_true',help='Assert saved control outputs; trace calls 0.')
 parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
 args=parser.parse_args()
 supplied=args.author_source.resolve(); SOURCE=supplied/'src' if (supplied/'src/avf_spline_generator/core.py').is_file() else supplied
 SCENE=args.scene_dir.resolve(); OUT=args.output_dir.resolve(); OUT.mkdir(parents=True,exist_ok=True)
 if SCENE==OUT: parser.error('--output-dir must be separate from the parent --scene-dir')
 PLAN=make_plan()
 try: validate_scene()
 except (Stop,OSError,KeyError,ValueError) as exc: parser.error(str(exc))
 sys.exit(check_outputs() if args.check else worker() if args.worker else supervise())
