#!/usr/bin/env python3
"""One fixed, artificial two-sheet/ridge diagnostic on Linux; exact bee798f7 methods.

The original Apache-2.0 tracer stays in its external checkout.
Artificial fields and diagnostic caller: Blucca / Codex.
"""
import argparse, datetime, hashlib, json, os, resource, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
SOURCE = None  # Set by the required external-source argument.
PIN = 'bee798f72751169065fe020d4ad02c52519c2d2b'
EXPECTED = {
 'core.py':'1bd16ef7ef1156e0657b2db541290b76af22632102bd0d4742be7013707e0364',
 'tracing.py':'b23618422a86dafd65049f2b9c8ef8edddabbfaaad4d883d1f90f7cafa61e839',
 'prepare.py':'a9a9eef67c5070b5fb95705a054048bb899d46cffeb334611170e0b0d4eba254',
 'storage.py':'866cdd2a4c6755c268b6688aa1dad5dbaa171361a645a247d8574013abcc4adf',
}
PLAN = {
 'source_pin':PIN, 'input_kind':'artificial native CT and V/H prediction fields',
 'native_shape_zyx':[40,40,128], 'tracing_shape_zyx':[20,20,64],
 'physical_A_z_tracing':8.0, 'physical_B_separation_tracing':{
  'x_le_16':4.0, 'cosine_transition_16_to_32':[4.0,1.15],
  'cosine_transition_32_to_48':[1.15,2.0], 'x_ge_48':2.0},
 'V_A_amplitude_u8':[240.0,180.0], 'V_B_amplitude_u8':[180.0,255.0],
 'amplitude_cosine_transition_x_tracing':[16.0,32.0],
 'fiber_cross_section_sigma_native_vox':0.90, 'H_constant_u8':8.0,
 'CT_background':20.0, 'CT_sheet_amplitude':90.0, 'CT_normal_sigma_native':0.35,
 'seed_rule':'nearest prepared primary/secondary seed to A/y=10, x=8..12; correct A x=50..54; max |z-A|,|y-10| <=0.6; ties descending centrality; absent=>fixed manual probe, explicitly flagged',
 'core_parameters':{'min_raw_len':7.5,'step_size':0.75,'max_low_steps':3,'core_r':2.05},
 'scenario_runs':1, 'paired_calls':['initial A trace','correct-layer zero-coverage trace','correct-layer trace using first raw coverage'],
 'resource_caps':{'seconds':120,'child_RSS_MiB':512,'threads':1},
 'configuration_searches':0, 'real_operator_frequency':'awaits actual operator fields/events',
}
def save(name,obj):
 (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def hashes():
 return {n:hashlib.sha256((SOURCE/'avf_spline_generator'/n).read_bytes()).hexdigest() for n in EXPECTED}
def check():
 import numpy as np
 s=json.loads((HERE/'summary.json').read_text())
 assert s['status']=='complete', s
 assert s['source_sha256_before']==s['source_sha256_after']==EXPECTED
 assert s['input_manifest']['native_shape_zyx']==PLAN['native_shape_zyx']
 assert s['input_manifest']['artificial_physical_labels'] is True
 for k in ['initial_raw','initial_finished','correct_seed_zero_coverage_raw']:
  assert s[k]['family_invalid_segments']==0, (k,s[k])
 assert s['coverage']['before']['count']==0
 assert s['coverage']['after']['is_covered_same_dir']==s['coverage']['after_native_function_call']
 if s['coverage']['after']['is_covered_same_dir']:
  assert s['correct_seed_with_raw_coverage']['curve_count']==0
 assert s['peak_child_RSS_kib']<=512*1024
 assert s['worker_elapsed_seconds']<=120
 with np.load(HERE/'curves.npz',allow_pickle=False) as z:
  assert len(z['initial_raw_points'])==s['initial_raw']['points']
 save('assert-check.json',{'status':'passed','source_pin':PIN,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scientific_mechanism_result':s['mechanism']})
 print('ASSERT PASSED',s['mechanism'])
def worker():
 t0=time.monotonic()
 import numpy as np, scipy, numba
 sys.path.insert(0,str(SOURCE))
 from avf_spline_generator import core,prepare,tracing,storage
 assert hashes()==EXPECTED
 work=HERE/'work'; work.mkdir(exist_ok=True)
 def mix(x,a,b,lo,hi):
  u=np.clip((x-lo)/(hi-lo),0,1)
  return a+(b-a)*(0.5-0.5*np.cos(np.pi*u))
 def sep(x):
  return np.where(x<=32,mix(x,4.0,1.15,16,32),mix(x,1.15,2.0,32,48))
 z,y,x=np.indices(tuple(PLAN['native_shape_zyx']),dtype='f4')
 qx=(x-0.5)*0.5
 az=np.full_like(x,16.5); bz=16.5+2*sep(qx)
 aa=mix(qx,240,180,16,32); ba=mix(qx,180,255,16,32)
 dy=y-20.5
 v=(aa*np.exp(-((z-az)**2+dy**2)/(2*0.9**2))+ba*np.exp(-((z-bz)**2+dy**2)/(2*0.9**2))).clip(0,255)
 p=np.stack([v,np.full_like(v,8.0)]).astype('f4')/255.0
 np.save(HERE/'native-predictions.npy',p)
 ct=20+90*np.exp(-(z-az)**2/(2*0.35**2))+90*np.exp(-(z-bz)**2/(2*0.35**2))
 np.save(HERE/'artificial-native-ct.npy',np.rint(ct).clip(0,255).astype('u1'))
 del z,y,x,qx,az,bz,aa,ba,dy,v,p,ct
 native=storage.Predictions(HERE/'native-predictions.npy',order='VH')
 pooled=prepare.prepare_tracing(native,None,work)
 axes=prepare.prepare_axes(pooled,work)
 fam=work/'family-1'
 presence,cent,seed_field=prepare.prepare_family(pooled,axes,1,fam,'cpu')
 coordinates,catalog=prepare.prepare_seeds(cent,seed_field,fam)
 sampler=storage.NativeSampler(native,cache_mib=8,chunk=64)
 def select(lo,hi,target):
  c=np.asarray(coordinates)
  ids=np.flatnonzero((c[:,2]>=lo)&(c[:,2]<=hi)&(np.abs(c[:,0]-8)<=0.6)&(np.abs(c[:,1]-10)<=0.6))
  if len(ids):
   cs=c[ids]; distance=(cs[:,0]-8)**2+(cs[:,1]-10)**2+(cs[:,2]-target)**2
   order=np.lexsort((-np.asarray(cent[tuple(cs.T)],dtype='i8'),distance))
   q=cs[order[0]].astype('i4'); actual=True
  else: q=np.array([8,10,target],dtype='i4'); actual=False
  return q,{'zyx':q.tolist(),'xyz':q[::-1].tolist(),'generated_native_seed':actual,'seed_flag':int(seed_field[tuple(q)]),'presence_u8':int(presence[tuple(q)]),'centrality_u16':int(cent[tuple(q)])}
 first,first_meta=select(8,12,10)
 correct,correct_meta=select(50,54,52)
 def covs(): return [np.zeros(presence.shape,'u1') for _ in range(3)]
 def probe(cov,q):
  zz,yy,xx=map(int,q); ux,uy,uz=core.decode_dir(axes[0][zz,yy,xx],axes[1][zz,yy,xx])
  return {'count':int(cov[0][zz,yy,xx]),'direction_bytes':[int(cov[1][zz,yy,xx]),int(cov[2][zz,yy,xx])],'direction_xyz':[float(ux),float(uy),float(uz)],'is_covered_same_dir':bool(core.is_covered_same_dir(*cov,xx,yy,zz,ux,uy,uz))}
 def trace_one(q,cov,flag):
  pts=np.empty((2048,3),'f4'); tans=np.empty_like(pts); offsets=np.zeros(129,'i8')
  zz,yy,xx=(np.array([i],dtype='i4') for i in q)
  n,k=core.trace_seed_range(cent,presence,*axes,zz,yy,xx,*cov,pts,tans,offsets,0,0,0,1,n_pass1=1 if flag==2 else 0,**PLAN['core_parameters'])
  return pts[:n].copy(),tans[:n].copy(),offsets[:k+1].copy()
 def stats(points,offsets):
  curves=[]; total_arc=0.0; invalid=0; segments=0; longest=0.0
  for a,b in zip(offsets[:-1],offsets[1:]):
   pp=points[a:b]; lengths=np.linalg.norm(np.diff(pp,axis=0),axis=1)
   arc=float(lengths.sum(dtype='f8')); total_arc+=arc; longest=max(longest,arc)
   vv=tracing.valid_segments(pp,pooled,1,sampler); invalid+=int((~vv).sum()); segments+=len(vv)
   ia=int(np.argmin(pp[:,0])); ib=int(np.argmax(pp[:,0])); labels=np.where(abs(pp[:,2]-8)<=abs(pp[:,2]-(8+sep(pp[:,0]))),'A','B')
   order=np.argsort(pp[:,0],kind='stable'); sortedp=pp[order]; sortedlabels=labels[order]
   # Right-hand physical B tail; boundary rows within contact are kept separate.
   tail_start=len(sortedp)-1
   while tail_start>0 and sortedlabels[tail_start-1]=='B': tail_start-=1
   tail=sortedp[tail_start:] if sortedlabels[-1]=='B' else np.empty((0,3))
   tail_arc=float(np.linalg.norm(np.diff(tail,axis=0),axis=1).sum(dtype='f8')) if len(tail)>1 else 0.0
   def end(i): return {'xyz_tracing':pp[i].astype(float).tolist(),'xyz_native':(pp[i]*2+.5).astype(float).tolist(),'artificial_sheet':str(labels[i]),'normal_distance_A_tracing':float(abs(pp[i,2]-8)),'normal_distance_B_tracing':float(abs(pp[i,2]-(8+sep(pp[i,0]))))}
   curves.append({'points':len(pp),'arc_tracing_vox':arc,'arc_native_vox':2*arc,'raw_order_start':end(0),'raw_order_end':end(-1),'left_endpoint':end(ia),'right_endpoint':end(ib),'artificial_B_tail_arc_tracing_vox':tail_arc,'family_segments':len(vv),'family_invalid_segments':int((~vv).sum())})
  return {'curve_count':len(curves),'points':len(points),'family_segments':segments,'family_invalid_segments':invalid,'arc_tracing_vox':total_arc,'arc_native_vox':2*total_arc,'longest_curve_arc_tracing_vox':longest,'curves':curves}
 coverage=covs(); before=probe(coverage,correct)
 pts,tans,offsets=trace_one(first,coverage,first_meta['seed_flag'])
 after=probe(coverage,correct)
 final,final_offsets=tracing.finish(pts,offsets,pooled,presence,1,sampler)
 control_pts,control_tans,control_offsets=trace_one(correct,covs(),correct_meta['seed_flag'])
 suppressed_pts,suppressed_tans,suppressed_offsets=trace_one(correct,[c.copy() for c in coverage],correct_meta['seed_flag'])
 initial=stats(pts,offsets); finished=stats(final,final_offsets); control=stats(control_pts,control_offsets); suppressed=stats(suppressed_pts,suppressed_offsets)
 jumped=any(c['left_endpoint']['artificial_sheet']=='A' and c['right_endpoint']['artificial_sheet']=='B' and c['artificial_B_tail_arc_tracing_vox']>=8 for c in initial['curves'])
 finished_jump=any(c['left_endpoint']['artificial_sheet']=='A' and c['right_endpoint']['artificial_sheet']=='B' and c['artificial_B_tail_arc_tracing_vox']>=8 for c in finished['curves'])
 mechanism={'artificial_raw_A_to_B_persistent_tail':jumped,'artificial_finished_A_to_B_persistent_tail':finished_jump,'raw_and_finished_all_family_valid':initial['family_invalid_segments']==finished['family_invalid_segments']==0,'correct_A_seed_generated_by_native_prepare':correct_meta['generated_native_seed'],'correct_A_seed_coverage_suppressed':after['is_covered_same_dir'],'correct_A_seed_yields_curve_before_coverage':control['curve_count']>0,'correct_A_seed_yields_curve_after_coverage':suppressed['curve_count']>0,'joint_mechanism_on_artificial_scene':jumped and finished_jump and after['is_covered_same_dir'] and control['curve_count']>0 and suppressed['curve_count']==0 and correct_meta['generated_native_seed']}
 np.savez_compressed(HERE/'curves.npz',initial_raw_points=pts,initial_raw_tangents=tans,initial_raw_offsets=offsets,initial_finished_points=final,initial_finished_offsets=final_offsets,correct_zero_coverage_points=control_pts,correct_zero_coverage_offsets=control_offsets,correct_with_coverage_points=suppressed_pts,correct_with_coverage_offsets=suppressed_offsets)
 save('summary.json',{'status':'complete','finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_pin':PIN,'source_sha256_before':EXPECTED,'source_sha256_after':hashes(),'versions':{'python':sys.version,'numpy':np.__version__,'scipy':scipy.__version__,'numba':numba.__version__},'input_manifest':{'native_shape_zyx':list(native.shape),'tracing_shape_zyx':list(presence.shape),'native_ct':'artificial-native-ct.npy','native_P':'native-predictions.npy','artificial_physical_labels':True,'CT_consumed_by_original_tracer':False,'frame':'native XYZ = 2*tracing XYZ + .5; arrays ZYX'},'generated_seed_catalog':catalog,'first_seed':first_meta,'correct_A_seed':correct_meta,'coverage':{'before':before,'after':after,'after_native_function_call':after['is_covered_same_dir'],'committed_object':'initial raw trace spans, before finish'},'initial_raw':initial,'initial_finished':finished,'correct_seed_zero_coverage_raw':control,'correct_seed_with_raw_coverage':suppressed,'retention_raw_to_finish_arc_ratio':finished['arc_tracing_vox']/initial['arc_tracing_vox'] if initial['arc_tracing_vox'] else None,'mechanism':mechanism,'worker_elapsed_seconds':time.monotonic()-t0,'peak_child_RSS_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_operator_event_frequency':None,'configuration_searches':0,'source_changes':0})
 print(json.dumps(mechanism,ensure_ascii=False))
def supervise():
 # Bounded Linux diagnostic: /proc RSS and ru_maxrss use KiB here.
 # Other host support can replace this supervisor when a real run needs it.
 save('plan.json',PLAN); save('source-refs.json',{'source_pin':PIN,'local_source':str(SOURCE),'sha256':hashes(),'urls':{n:f'https://github.com/Qualzz/AVF_SPLINE_GENERATOR/blob/{PIN}/src/avf_spline_generator/{n}' for n in EXPECTED}})
 assert hashes()==EXPECTED
 env=dict(os.environ,NUMBA_NUM_THREADS='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMBA_CACHE_DIR=str(HERE/'jit-cache'),PYTHONDONTWRITEBYTECODE='1')
 begin=time.monotonic(); peak=0; reason=None
 with (HERE/'run.stdout').open('w') as out,(HERE/'run.stderr').open('w') as err:
  child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--worker','--author-source',str(SOURCE),'--output-dir',str(HERE)],cwd=str(Path.cwd()),env=env,stdout=out,stderr=err)
  while child.poll() is None:
   try:
    status=Path(f'/proc/{child.pid}/status').read_text()
    rss=int(next(line.split()[1] for line in status.splitlines() if line.startswith('VmRSS:'))); peak=max(peak,rss)
   except (FileNotFoundError,StopIteration): pass
   if peak>512*1024: reason='RSS cap exceeded'; break
   if time.monotonic()-begin>120: reason='120 second cap exceeded'; break
   time.sleep(.05)
  if reason:
   child.terminate()
   try: child.wait(timeout=2)
   except subprocess.TimeoutExpired: child.kill(); child.wait()
  code=child.returncode
 save('run-result.json',{'exit_code':code,'supervisor_seconds':time.monotonic()-begin,'observed_peak_child_RSS_kib':peak,'resource_stop_reason':reason})
 if code!=0 or reason:
  if not (HERE/'summary.json').exists(): save('summary.json',{'status':'failed','exit_code':code,'reason':reason or 'runner failure; see run.stderr','source_pin':PIN,'source_sha256_after':hashes(),'scenario_runs':1})
  print((HERE/'run.stderr').read_text()[-7000:]); return code or 1
 check(); return 0
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--author-source',type=Path,required=True,help='Existing exact bee798f7 author checkout root or its src directory; source remains external and unmodified.')
 parser.add_argument('--output-dir',type=Path,required=True,help='Artifact directory, preferably a workspace temp directory.')
 parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS); parser.add_argument('--check',action='store_true',help='Assert saved outputs without rerunning tracing.'); a=parser.parse_args()
 if a.author_source:
  supplied=a.author_source.resolve()
  SOURCE=supplied/'src' if (supplied/'src/avf_spline_generator/core.py').is_file() else supplied
 if a.output_dir:
  HERE=a.output_dir.resolve(); HERE.mkdir(parents=True,exist_ok=True)
 if a.worker: worker()
 elif a.check: check()
 else: sys.exit(supervise())
