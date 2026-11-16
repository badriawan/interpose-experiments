"""Stage10 scoped bridge to official conversion/evaluation in the verified env.

No environment installation, source checkout mutation, or LLM calls occur here.
The caller passes the same six values as official run_maskedmimic.sh.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE.parent/'trial_01'))
from launcher import settings
_CONFIG = settings.load_config()
ROOT = Path(_CONFIG['paths']['protomotions_root'])
LAUNCHER = HERE / 'run_simulator.sh'
METRICS = '[cartesian_err,gt_err,dv_rew,kb_rew,lr_rew,rv_rew,rav_rew,gr_err,gr_err_degrees,masked_gt_err,masked_gr_err,masked_gr_err_degrees]'


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child_environment(output):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('OPENAI_', 'AZURE_OPENAI_', 'ANTHROPIC_', 'GEMINI_', 'MISTRAL_', 'COHERE_')) or key in ('GOOGLE_API_KEY', 'INTERPOSE_API_KEY_FILE'):
            env.pop(key, None)
    env['STAGE10_SIM_DIR'] = str(output)
    env['CUDA_VISIBLE_DEVICES'] = '0'
    return env


def evaluation_arguments(model_path, control_setting, input_smpl_path, input_control_path, output_path):
    if control_setting not in ('hands', 'pelvis_position'):
        raise ValueError('Unsupported conditioning setting for the Stage10 official executor')
    return [
        '+robot=smpl', '+simulator=isaacgym', '+opt=masked_mimic/constraints/' + control_setting,
        '+motion_file=' + str(input_smpl_path), '+checkpoint=' + str(model_path),
        '+force_flat_terrain=True', '+ngpu=1', '+eval_overrides.ngpu=1',
        '+eval_compute_metrics=True', '+headless=True', '+terrain=flat', '+save_motion=True',
        'hydra.run.dir=' + str(output_path), '+agent.config.eval_metric_keys=' + METRICS,
        '+env.config.masked_mimic.user_control_folder=' + str(input_control_path),
        '+eval_overrides.num_envs=1', '+env.config.num_envs=1', '+num_envs=1',
        '+agent.config.eval_num_episodes=1', '+agent.config.eval_length=null',
        '+agent.config.success_threshold=0.5', '+fabric.loggers=null',
    ]


def _next_attempt(output):
    return 1 + len(list(output.glob('stage10_conversion_attempt_*.log'))) + len(list(output.glob('stage10_evaluation_attempt_*.log')))


def _wait_for_repair(kind, output, attempt, log, reason):
    """No autonomous retry: only a matching explicit primary sentinel resumes."""
    failure_id = '{}_{:02d}'.format(kind, attempt)
    failure = {'failure_id': failure_id, 'kind': kind, 'attempt': attempt,
               'log': str(log), 'reason': reason, 'status': 'WAITING_FOR_REPAIR',
               'timestamp': datetime.now().astimezone().isoformat()}
    _write(output / ('stage10_failure_' + failure_id + '.json'), failure)
    _write(output / 'stage10_pending_failure.json', failure)
    if log.exists():
        print('\n'.join(log.read_text(errors='replace').splitlines()[-28:]), flush=True)
    if os.environ.get('STAGE10_WAIT_FOR_REPAIR', os.environ.get('STAGE8_WAIT_FOR_REPAIR')) != '1':
        raise RuntimeError(reason + '; log ' + str(log))
    print('STAGE10_WAIT_FOR_REPAIR ' + json.dumps(failure), flush=True)
    request = output / 'stage10_retry_request.json'
    while True:
        if request.is_file():
            try:
                action = json.loads(request.read_text())
            except (OSError, ValueError):
                action = {}
            if action.get('failure_id') == failure_id and action.get('action') in ('retry', 'abort'):
                consumed = output / ('stage10_retry_request_consumed_' + failure_id + '.json')
                if consumed.exists():
                    raise RuntimeError('Retry sentinel already consumed; refusing repeated authorization')
                request.rename(consumed)
                failure['status'] = 'RETRY_AUTHORIZED' if action['action'] == 'retry' else 'ABORTED'
                _write(output / 'stage10_pending_failure.json', failure)
                if action['action'] == 'abort':
                    raise RuntimeError('Primary aborted after child failure; preserved log ' + str(log))
                print('STAGE10_REPAIR_RETRY_AUTHORIZED ' + failure_id, flush=True)
                return
        time.sleep(1)


def _run_step_once(kind, command, output, attempt, env):
    log = output / ('stage10_{}_attempt_{:02d}.log'.format(kind, attempt))
    record = {'kind': kind, 'attempt': attempt, 'started_at': datetime.now().astimezone().isoformat(),
              'cwd': str(ROOT), 'command': command, 'log': str(log)}
    start = time.monotonic()
    with log.open('x') as handle:
        handle.write('$ ' + shlex.join(command) + '\n\n')
        handle.flush()
        try:
            completed = subprocess.run(command, cwd=str(ROOT), env=env,
                stdout=handle, stderr=subprocess.STDOUT, check=False)
            record['exit'] = completed.returncode
        except OSError as error:
            record['exit'] = 127
            handle.write(type(error).__name__ + ': ' + str(error) + '\n')
        record['elapsed_s'] = round(time.monotonic() - start, 6)
        handle.write('\n[exit={}; elapsed_s={}]\n'.format(record['exit'], record['elapsed_s']))
    with (output / 'stage10_bridge_commands.jsonl').open('a') as handle:
        handle.write(json.dumps(record) + '\n')
    print('STAGE10_CHILD {} exit={} elapsed_s={} log={}'.format(kind, record['exit'], record['elapsed_s'], log), flush=True)
    return record


def _run_step(kind, command, output, attempt, env):
    while True:
        record = _run_step_once(kind, command, output, attempt, env)
        if not record['exit']:
            return record
        if kind == 'evaluation' and (output / 'execution_evidence.json').exists():
            archived = output / ('stage10_failed_evaluation_evidence_{:02d}.json'.format(attempt))
            if not archived.exists():
                archived.write_bytes((output / 'execution_evidence.json').read_bytes())
        _wait_for_repair(kind, output, attempt, Path(record['log']),
            'First failed simulator child: {} (exit {})'.format(kind, record['exit']))
        attempt = _next_attempt(output)


def run_maskedmimic(model_path, control_setting, input_folder, input_smpl_path, input_control_path, output_path):
    """Run official conversion then one finite official MaskedMimic evaluation.

    Successful conversion is reused. Existing eval outputs are never overwritten;
    interrupted attempts retain all evidence and use a new numbered child log.
    """
    model, folder, motion, controls, output = [Path(p).expanduser().absolute() for p in
        (model_path, input_folder, input_smpl_path, input_control_path, output_path)]
    if control_setting not in ('hands', 'pelvis_position'):
        raise ValueError('Unsupported conditioning setting')
    if not model.is_file() or not folder.is_dir() or not controls.is_dir():
        raise FileNotFoundError('Checkpoint, template folder or control folder missing')
    output.mkdir(parents=True, exist_ok=True)
    template_folder = motion.parent.name
    if not template_folder.endswith('-smpl'):
        raise ValueError('Expected official converted task_N-smpl folder')
    template = folder / template_folder[:-5] / (motion.stem + '.npz')
    if not template.is_file():
        raise FileNotFoundError('Corresponding source template is missing: ' + str(template))
    control_files = sorted(controls.glob('*.npz'))
    if not control_files:
        raise FileNotFoundError('No official control NPZ input')
    signature = {'template': str(template), 'template_sha256': _digest(template),
                 'control_setting': control_setting,
                 'controls_sha256': {str(p): _digest(p) for p in control_files},
                 'checkpoint': str(model)}
    signature_path = output / 'stage10_input_signature.json'
    if signature_path.exists() and json.loads(signature_path.read_text()) != signature:
        raise RuntimeError('Inputs changed for an existing task output; preserve it and select a new task/output instead of overwriting')
    if not signature_path.exists():
        _write(signature_path, signature)
    final_output = output / 'trajectory_pose_aa_0_0.npz'
    evidence_path = output / 'execution_evidence.json'
    if final_output.exists():
        evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
        if evidence.get('status') == 'PASS' and final_output.stat().st_size > 0:
            print('STAGE10_REUSE successful official evaluation ' + str(final_output), flush=True)
            return final_output
        raise RuntimeError('Partial/existing official result retained; inspect its evidence before a new evaluation')
    env = child_environment(output)
    attempt = _next_attempt(output)
    conversion_marker = output / 'stage10_conversion_success.json'
    if motion.exists():
        marker = json.loads(conversion_marker.read_text()) if conversion_marker.exists() else None
        if not marker or marker['template_sha256'] != signature['template_sha256'] or marker['motion_sha256'] != _digest(motion):
            raise RuntimeError('Converted motion exists without matching successful-conversion evidence; retained without repeating conversion')
        print('STAGE10_REUSE successful official conversion ' + str(motion), flush=True)
    else:
        conversion = ['bash', str(LAUNCHER), str(HERE / 'sim_convert_bootstrap.py'), str(folder), '--humanoid-type=smpl']
        while True:
            record = _run_step('conversion', conversion, output, attempt, env)
            # Official converter catches per-file exceptions and may return exit0.
            if motion.is_file() and motion.stat().st_size > 0:
                break
            _wait_for_repair('conversion', output, record.get('attempt', attempt), Path(record.get('log', output / 'conversion.log')),
                'Official converter exited0 but expected motion is absent/empty: ' + str(motion))
            attempt = _next_attempt(output)
        _write(conversion_marker, {'template_sha256': signature['template_sha256'], 'motion_sha256': _digest(motion), 'motion': str(motion)})
    command = ['bash', str(LAUNCHER), str(HERE / 'sim_eval_bootstrap.py')]
    command += evaluation_arguments(model, control_setting, motion, controls, output)
    _run_step('evaluation', command, output, attempt, env)
    if not final_output.is_file() or final_output.stat().st_size == 0:
        raise RuntimeError('Evaluation exited0 without expected official result: ' + str(final_output))
    evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    if evidence.get('status') != 'PASS':
        raise RuntimeError('Evaluation result exists but observation evidence is not PASS')
    return final_output
