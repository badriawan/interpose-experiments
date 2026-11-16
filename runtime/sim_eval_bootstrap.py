"""Run the official eval entry point with observation-only evidence hooks.

No model/control math changes. Saves raw official recorder buffers and blocks
external Python socket connections; localhost remains available to Fabric/DDP.
"""
import atexit,ipaddress,json,os,runpy,sys,time,traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'trial_01'))
from launcher import settings
CONFIG=settings.load_config(); settings.verify_runtime_manifest()
ROOT=Path(CONFIG['paths']['protomotions_root'])
for path in (ROOT, Path(CONFIG['paths']['smplsim_root']), Path(CONFIG['paths']['isaacgym_python_root'])):
 sys.path.insert(0,str(path))
OUT=Path(os.environ['STAGE10_SIM_DIR']);OUT.mkdir(parents=True,exist_ok=True)
report={'status':'RUNNING','official_entrypoint':str(ROOT/'protomotions/eval_agent.py'),'checkpoint_loaded':False,'policy_calls':0,'actions_all_finite':True,'external_connections_blocked':0,'external_connections_allowed':0,'llm_modules_loaded':False,'training_called':False,'config_only':'--cfg' in sys.argv}
start=time.monotonic();envs=[];actions=[]
for key in list(os.environ):
 if key.startswith(('OPENAI_', 'AZURE_OPENAI_', 'ANTHROPIC_', 'GEMINI_', 'MISTRAL_', 'COHERE_')) or key in ('GOOGLE_API_KEY', 'INTERPOSE_API_KEY_FILE'):os.environ.pop(key,None)
def audit(event,args):
 if event!='socket.connect':return
 address=args[1]
 if not isinstance(address,tuple):return  # Local Unix socket, not Internet.
 host=str(address[0]);local=host in ('localhost','127.0.0.1','::1')
 try:local=local or ipaddress.ip_address(host).is_loopback
 except ValueError:pass
 if not local:
  report['external_connections_blocked']+=1
  raise RuntimeError('External network is disabled for Stage10 evaluation')
sys.addaudithook(audit)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from clock_schema import validate_clock_evidence
sys.path.insert(0,str(ROOT/'protomotions'))  # Restore official script directory under Python -I.
try:
 import isaacgym  # Required before torch; same ordering as official CLI.
 import torch,numpy as np
 from protomotions.envs.base_env.env import BaseEnv
 from protomotions.agents.ppo.agent import PPO
 from protomotions.agents.masked_mimic.model import VaeDeterministicOutputModel
 from protomotions.envs.mimic.env import Mimic
 report['purpose']='Stage10 custom interaction: every-frame simulator clock observation'
 report['clock_steps']=[];report['clock_records']=[];report['reset_clocks']=[]
 report['clock_observed_environment_index']=0;report['object_clock_measured']=False
 def clocks(env):
  return {'motion_time_s':float(env.motion_manager.motion_times[0].item()),'sdk_time_s':float(env.simulator._gym.get_sim_time(env.simulator._sim))}
 old_step=BaseEnv.step
 def observed_step(self,*args,**kwargs):
  before=clocks(self);value=old_step(self,*args,**kwargs);after=clocks(self)
  report['clock_steps'].append({'before':before,'after':after});return value
 BaseEnv.step=observed_step
 old_reset=Mimic.reset
 def observed_reset(self,*args,**kwargs):
  value=old_reset(self,*args,**kwargs);report['reset_clocks'].append(clocks(self));return value
 Mimic.reset=observed_reset
 old_store=PPO.store_motion_data
 def observed_store(self,*args,**kwargs):
  report['clock_records'].append(clocks(self.env));return old_store(self,*args,**kwargs)
 PPO.store_motion_data=observed_store
 old_init=BaseEnv.__init__
 def observed_init(self,*args,**kwargs):
  value=old_init(self,*args,**kwargs);envs.append(self);return value
 BaseEnv.__init__=observed_init
 old_load=PPO.load
 def observed_load(self,checkpoint):
  value=old_load(self,checkpoint)
  report['checkpoint_loaded']=True;report['checkpoint']=str(Path(checkpoint).resolve())
  report['model_parameter_count']=sum(p.numel() for p in self.model.parameters())
  report['env_dt']=float(self.env.dt);report['num_envs']=int(self.num_envs)
  report['motion_count']=int(self.motion_lib.num_motions());report['reference_motion_lengths_s']=self.motion_lib.state.motion_lengths.detach().cpu().tolist()
  print('STAGE10_CHECKPOINT_LOAD_RETURNED '+json.dumps({k:report[k] for k in ['checkpoint_loaded','model_parameter_count','num_envs','env_dt','motion_count']}),flush=True)
  return value
 PPO.load=observed_load
 old_act=VaeDeterministicOutputModel.act
 def observed_act(self,*args,**kwargs):
  value=old_act(self,*args,**kwargs);finite=bool(torch.isfinite(value).all().item());report['policy_calls']+=1;report['actions_all_finite']=report['actions_all_finite'] and finite
  assert finite,'non-finite policy action'
  actions.append(value.detach().cpu().numpy().copy());return value
 VaeDeterministicOutputModel.act=observed_act
 old_write=PPO.write_recordings
 def observed_write(self,motion_ids,*args,**kwargs):
  # Buffers are already CPU snapshots made by official store_motion_data.
  arrays={key:torch.stack(values).numpy() for key,values in self.motion_recording.items() if values and isinstance(values[0],torch.Tensor)}
  assert arrays and all(np.isfinite(v).all() for v in arrays.values()),'invalid official raw recorder buffers'
  arrays.update(dt=np.asarray(float(self.env.dt)),body_names=np.asarray(self.env.config.robot.body_names),actions=np.stack(actions))
  arrays.update(recorder_reference_time_s=np.asarray([row['motion_time_s'] for row in report['clock_records']],dtype=np.float64),recorder_sdk_time_s=np.asarray([row['sdk_time_s'] for row in report['clock_records']],dtype=np.float64))
  if report['reset_clocks']:
   arrays.update(last_reset_reference_time_s=np.asarray(report['reset_clocks'][-1]['motion_time_s']),last_reset_sdk_time_s=np.asarray(report['reset_clocks'][-1]['sdk_time_s']))
  raw=OUT/'stage10_raw_trajectory.npz';assert not raw.exists(),'refuse raw output overwrite';np.savez(raw,**arrays)
  report['raw_trajectory']=str(raw);report['recorded_frames']=len(arrays['root_pos'])
  return old_write(self,motion_ids,*args,**kwargs)
 PPO.write_recordings=observed_write
 # Never enter training even if a later config change selects a wrong path.
 def forbidden_training(*args,**kwargs):
  report['training_called']=True;raise RuntimeError('Training is outside Stage10 scope')
 PPO.fit=forbidden_training
 from protomotions.agents.masked_mimic.agent import MaskedMimic
 MaskedMimic.fit=forbidden_training
 sys.argv=[str(ROOT/'protomotions/eval_agent.py')]+sys.argv[1:]
 runpy.run_path(str(ROOT/'protomotions/eval_agent.py'),run_name='__main__')
 if not report['config_only']:
  assert report['checkpoint_loaded'] and report['policy_calls']>1 and report.get('recorded_frames',0)>1
  report['clock_validation']=validate_clock_evidence(report)
  assert report['clock_validation']['status']=='PASS','recorder clock observation validation failed'
 report['status']='PASS'
except BaseException as e:
 report['status']='FAIL';report['error_type']=type(e).__name__;report['error']=str(e);report['traceback']=traceback.format_exc();raise
finally:
 for env in envs:
  try:env.simulator.close()
  except Exception as e:report.setdefault('cleanup_errors',[]).append(type(e).__name__+': '+str(e))
 if 'torch' in sys.modules:
  t=sys.modules['torch']
  if t.cuda.is_initialized():
   report['cuda_peak_allocated_bytes']=t.cuda.max_memory_allocated();report['cuda_peak_reserved_bytes']=t.cuda.max_memory_reserved()
 report['llm_modules_loaded']=any(n in sys.modules for n in ['openai','autogen','anthropic'])
 report['elapsed_s']=time.monotonic()-start
 (OUT/'execution_evidence.json').write_text(json.dumps(report,indent=2)+'\n')
 print('STAGE10_EVIDENCE '+json.dumps({k:v for k,v in report.items() if k not in ('traceback','checkpoint')}),flush=True)
