# Adapted from InterPose (Copyright 2025 Yangsong ZHANG) and local experiment code.
# InterPose MIT license: ../../third_party/InterPose-LICENSE.txt (repository third_party).
"""Deferred executor/bridge adapter and CPU artifact verification.

Importing this module does not import Torch, Isaac Gym, OpenAI or the executor.
Runtime caches are scoped to the repository private .local directory.
"""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np


class RuntimeFailure(RuntimeError):
    """A runtime/input artifact failure which must not cause another dispatch."""


_CREDENTIAL_PREFIXES = ('OPENAI_', 'AZURE_OPENAI_', 'ANTHROPIC_', 'GEMINI_',
                        'MISTRAL_', 'COHERE_')
_CREDENTIAL_NAMES = {'GOOGLE_API_KEY', 'INTERPOSE_API_KEY_FILE'}
_OLD_FLAGS = ('STAGE8_RESUME', 'STAGE8_WAIT_FOR_REPAIR', 'STAGE10_WAIT_FOR_REPAIR')
_PLAN_KEYS = {'control_joints', 'control_points', 'text', 'number_frames',
              'task_index', 'object_name', 'object_points'}


def _credential_name(name):
    return name.startswith(_CREDENTIAL_PREFIXES) or name in _CREDENTIAL_NAMES


def _scrub_child_environment(environment):
    cleaned = dict(environment)
    for name in list(cleaned):
        if _credential_name(name) or name in _OLD_FLAGS:
            cleaned.pop(name, None)
    return cleaned


def _owned(path, root):
    resolved = Path(path).expanduser().resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise RuntimeFailure('Runtime path escapes the fresh run root: ' + str(path))
    return resolved


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(Path(path).resolve()))
    if spec is None or spec.loader is None:
        raise RuntimeFailure('Cannot load verified runtime module: ' + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def _runtime_scope(context):
    repo = Path(context['repo_root']).resolve()
    executor_folder = str(Path(context['executor_file']).resolve().parent)
    old_cwd = Path.cwd()
    old_path = sys.path[:]
    affected = {name: value for name, value in os.environ.items()
                if _credential_name(name) or name in _OLD_FLAGS or name in
                ('CUDA_VISIBLE_DEVICES', 'HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE',
                 'WANDB_MODE', 'WANDB_DISABLED', 'MPLBACKEND', 'INTERPOSE_LAB_CONFIG')}
    missing = {name for name in ('CUDA_VISIBLE_DEVICES', 'HF_HUB_OFFLINE',
               'TRANSFORMERS_OFFLINE', 'WANDB_MODE', 'WANDB_DISABLED', 'MPLBACKEND', 'INTERPOSE_LAB_CONFIG')
               if name not in os.environ}
    module_names = ('stage10_simulator_bridge', 'waypoint_validation')
    previous_modules = {name: sys.modules.get(name) for name in module_names}
    try:
        for name in list(os.environ):
            if _credential_name(name) or name in _OLD_FLAGS:
                os.environ.pop(name, None)
        os.environ.update(CUDA_VISIBLE_DEVICES='0', HF_HUB_OFFLINE='1',
                          TRANSFORMERS_OFFLINE='1', WANDB_MODE='disabled',
                          WANDB_DISABLED='true', MPLBACKEND='Agg')
        os.environ['INTERPOSE_LAB_CONFIG'] = context['runtime_config']
        os.chdir(repo)
        sys.path[:0] = [executor_folder, str(repo)]
        yield
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_path
        for name in list(os.environ):
            if _credential_name(name) or name in _OLD_FLAGS:
                os.environ.pop(name, None)
        for name in missing:
            os.environ.pop(name, None)
        os.environ.update(affected)
        for name, previous in previous_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def _install_bridge(context, run_root):
    """Keep original HERE/ROOT for its read-only bootstrap dependencies."""
    bridge = _load_module('_latihan_verified_stage10_bridge', context['bridge_file'])
    original_run = bridge.run_maskedmimic
    original_environment = bridge.child_environment
    calls = {'count': 0}
    model = Path(context['model_path']).resolve()

    def child_environment(output):
        return _scrub_child_environment(original_environment(output))

    def run_maskedmimic(model_path, control_setting, input_folder, input_smpl_path,
                       input_control_path, output_path):
        if calls['count']:
            raise RuntimeFailure('Only one simulator bridge call is allowed per dispatch.')
        if Path(model_path).resolve() != model:
            raise RuntimeFailure('Simulator checkpoint differs from the preflight checkpoint.')
        folder, motion, controls, output = [_owned(p, run_root) for p in
            (input_folder, input_smpl_path, input_control_path, output_path)]
        if output.exists():
            raise RuntimeFailure('Simulator output already exists; refusing result reuse.')
        if control_setting != 'hands':
            raise RuntimeFailure('This exercise requires hand conditioning.')
        calls['count'] += 1
        return original_run(str(model), control_setting, str(folder), str(motion),
                            str(controls), str(output))

    bridge.child_environment = child_environment
    bridge.run_maskedmimic = run_maskedmimic
    sys.modules['stage10_simulator_bridge'] = bridge
    return calls


def dispatch(context, run_root, plan):
    """Perform exactly one real generation after the caller validated its plan.

    This function is deliberately not called by preflight/dry-run modes. A fresh
    marker and output directory prevent retries after partial failures. It does
    not claim success: the caller must separately call verify_artifacts.
    """
    root = Path(run_root).resolve()
    if not root.is_dir():
        raise RuntimeFailure('Fresh run directory is missing.')
    if set(plan) != _PLAN_KEYS or plan.get('task_index') != 1:
        raise RuntimeFailure('Exactly one task_index=1 generation plan is required.')
    if plan.get('object_name') != [context['state']['custom_goal']['object']]:
        raise RuntimeFailure('Plan object differs from the configured task.')
    _owned(context['data_folder'], root)
    output_root = _owned(root / 'output', root)
    if output_root.exists():
        raise RuntimeFailure('Run output already exists; refusing another dispatch.')
    marker = root / 'runtime_dispatch_started.json'
    with marker.open('x') as handle:
        json.dump({'status': 'DISPATCH_STARTED',
                   'started_at': datetime.now().astimezone().isoformat()}, handle)
        handle.write('\n')

    with _runtime_scope(context):
        bridge_calls = _install_bridge(context, root)
        # The executor uses an absolute module name. Rebind it explicitly so a
        # cached validator from another exercise cannot override this sibling.
        validator_path = Path(context['executor_file']).resolve().with_name('waypoint_validation.py')
        validator = _load_module('_latihan_verified_waypoint_validation', validator_path)
        sys.modules['waypoint_validation'] = validator
        module = _load_module('_latihan_copied_executor', context['executor_file'])
        options = SimpleNamespace(model_path=str(Path(context['model_path']).resolve()),
            data_folder=str(Path(context['data_folder']).resolve()), check_collision=True,
            multi_object_narrow_path=False, cond_mode='only_spatial', save_obj_only=True,
            executor='maskedmimic')
        actor = module.protomotion_model(device='cuda:0',
            save_motion_root=str(output_root), batch_size=1, vis_fps=15,
            use_sample_contact_point=True, last_k_frame=2, opt=options)
        parameters = context['body_parameters']
        actor.set_data_name(context['seq_name'], context['p_idx'], context['scene_name'],
            gender=parameters['gender'], betas=np.asarray([parameters['betas16']], dtype=float))
        returned = actor.generate_human_object(**plan)
        if returned is not None:
            raise RuntimeFailure('Executor did not generate an accepted motion: ' + str(returned))
        if bridge_calls['count'] != 1:
            raise RuntimeFailure('Generation returned without exactly one simulator bridge call.')
        actor.get_human_object_mesh()


def _file(path, root):
    path = _owned(path, root)
    if not path.is_file() or not path.stat().st_size:
        raise RuntimeFailure('Required fresh artifact missing or empty: ' + str(path))
    return path


def _finite_array(value, shape, label):
    array = np.asarray(value)
    if array.shape != shape or array.dtype.kind not in 'fiu' or not np.isfinite(array).all():
        raise RuntimeFailure('Invalid finite trajectory array: ' + label)
    return array


def _digest(path):
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def _verify_artifacts(context, run_root):
    """Verify generated data/evidence without importing any simulation modules."""
    root = Path(run_root).resolve()
    episode = _owned(root / 'output' / context['episode_name'], root)
    stem = context['seq_name'] + '_pidx_' + str(context['p_idx']) + '_task_0'
    motion_path = _file(episode / (stem + '.npy'), root)
    state_path = _file(episode / (stem + '.json'), root)
    sim_folder = episode / 'maskedmimic_res/task_0'
    pose_path = _file(sim_folder / 'trajectory_pose_aa_0_0.npz', root)
    evidence_path = _file(sim_folder / 'execution_evidence.json', root)
    evidence = json.loads(evidence_path.read_text())
    if (evidence.get('status') != 'PASS' or evidence.get('checkpoint_loaded') is not True
            or evidence.get('actions_all_finite') is not True
            or evidence.get('training_called') is not False
            or evidence.get('llm_modules_loaded') is not False
            or evidence.get('config_only') is not False
            or int(evidence.get('policy_calls', 0)) < 2
            or int(evidence.get('model_parameter_count', 0)) < 1
            or int(evidence.get('num_envs', 0)) != 1
            or evidence.get('clock_validation', {}).get('status') != 'PASS'):
        raise RuntimeFailure('Simulator evidence does not establish a finite evaluated clip.')
    if Path(evidence.get('checkpoint', '')).resolve() != Path(context['model_path']).resolve():
        raise RuntimeFailure('Simulator evidence checkpoint mismatch.')
    dt = float(evidence.get('env_dt', float('nan')))
    if not np.isfinite(dt) or abs(dt - 1. / 30) > 1e-6:
        raise RuntimeFailure('Simulator evidence has an incompatible timestep.')
    raw_path = _file(evidence.get('raw_trajectory', sim_folder / 'stage10_raw_trajectory.npz'), root)
    with np.load(pose_path, allow_pickle=False) as pose:
        if not {'pose', 'trans'}.issubset(pose.files):
            raise RuntimeFailure('Simulator pose/trans output is incomplete.')
        for name in ('pose', 'trans'):
            if not pose[name].size or not np.isfinite(pose[name]).all():
                raise RuntimeFailure('Simulator pose/trans output is not finite.')
    with np.load(raw_path, allow_pickle=False) as raw:
        if not {'root_pos', 'actions', 'dt'}.issubset(raw.files):
            raise RuntimeFailure('Raw simulator recorder evidence is incomplete.')
        raw_frames = len(raw['root_pos'])
        if raw_frames < 2 or raw['root_pos'].shape[1:] != (1, 3):
            raise RuntimeFailure('Raw simulator root shape is invalid.')
        for name in ('root_pos', 'actions'):
            if not raw[name].size or not np.isfinite(raw[name]).all():
                raise RuntimeFailure('Raw simulator recorder is not finite.')
        if len(raw['actions']) != raw_frames or abs(float(raw['dt']) - dt) > 1e-6:
            raise RuntimeFailure('Raw simulator frame/timestep evidence is inconsistent.')
    # Only the fresh, locally generated motion is unpickled; input bytes are not
    # accepted here as evidence of a successful generation.
    loaded = np.load(motion_path, allow_pickle=True)
    motion = loaded.item()
    if not isinstance(motion, dict):
        raise RuntimeFailure('Generated motion is not the expected dictionary.')
    human = motion.get('human', {})
    joint_pos = np.asarray(human.get('joint_xyz'))
    if joint_pos.ndim != 4 or joint_pos.shape[0] != 1 or joint_pos.shape[2:] != (24, 3):
        raise RuntimeFailure('Generated body position shape is invalid.')
    frames = joint_pos.shape[1]
    if not 1 < frames <= 901:
        raise RuntimeFailure('Generated frame count is outside the bounded exercise.')
    if raw_frames < frames or int(evidence.get('recorded_frames', 0)) != raw_frames:
        raise RuntimeFailure('Raw recorder does not cover the generated parent clip.')
    _finite_array(joint_pos, (1, frames, 24, 3), 'human.joint_xyz')
    _finite_array(human.get('pose_aa'), (1, frames, 22, 3), 'human.pose_aa')
    root_quat = _finite_array(human.get('orientation'), (1, frames, 1, 4), 'human.orientation')
    object_name = context['state']['custom_goal']['object']
    obj = motion.get('object', {}).get(object_name, {})
    _finite_array(obj.get('xyz'), (1, frames, 3), 'object.xyz')
    obj_quat = _finite_array(obj.get('rotation'), (1, frames, 4), 'object.rotation')
    if (np.max(np.abs(np.linalg.norm(root_quat, axis=-1) - 1)) > .001 or
            np.max(np.abs(np.linalg.norm(obj_quat, axis=-1) - 1)) > .001):
        raise RuntimeFailure('Generated root/object quaternion is not normalized.')
    metadata = motion.get('metadata', {})
    goal = context['state']['custom_goal']
    if (float(metadata.get('fps', 0)) != 30
            or metadata.get('custom_goal') != goal
            or metadata.get('custom_instruction') != context['state']['custom_instruction']
            or metadata.get('physical_success_verified') is not False
            or metadata.get('phase_sync_verified') is not False
            or int(metadata.get('frame_count', 0)) != frames):
        raise RuntimeFailure('Generated metadata does not match the task or scope.')
    validation = metadata.get('planned_lift_validation', {})
    required_hold = int(round(float(goal['hold_duration_s']) * 30))
    for kind in ('raw_plan', 'retimed_plan'):
        result = validation.get(kind, {})
        if result.get('status') != 'PASS' or result.get('hold_intervals') != required_hold:
            raise RuntimeFailure('Generated plan validation metadata is missing or inconsistent.')
    schedule = metadata.get('planned_hand_release_schedule', {})
    try:
        placed, start, end = [int(schedule[k]) for k in
            ('placement_frame', 'withdraw_start_frame', 'withdraw_end_frame')]
    except (KeyError, TypeError, ValueError):
        raise RuntimeFailure('Generated release schedule is missing.')
    if (not 0 <= placed < start < end == frames - 1
            or start - placed != round(float(goal['settle_duration_s']) * 30)
            or end - start != round(float(goal['hand_withdraw_duration_s']) * 30)
            or placed != validation['retimed_plan'].get('placement_frame')):
        raise RuntimeFailure('Generated release schedule is inconsistent with the clip.')
    output_state = json.loads(state_path.read_text())
    if output_state.get('custom_goal') != goal or not isinstance(output_state.get('human'), dict):
        raise RuntimeFailure('Final environment state is incomplete or belongs to another task.')
    for name in ('pelvis', 'left_hand', 'right_hand', 'orientation'):
        _finite_array(output_state['human'].get(name), (3,), 'state.human.' + name)
    if not isinstance(output_state.get('objects'), list) or not any(
            isinstance(obj, dict) and obj.get('name') == context['state']['custom_goal']['object']
            for obj in output_state['objects']):
        raise RuntimeFailure('Final environment state is missing the interacted object.')
    meshes = _owned(episode / 'objs_mesh', root)
    for index in range(frames):
        _file(meshes / ('{:05d}.ply'.format(index)), root)
        _file(meshes / ('{:05d}_object_{}.ply'.format(index, object_name)), root)
    return {'status': 'PASS', 'scope': 'fresh generated artifacts and bridge evidence only',
            'frames': int(frames), 'fps': 30, 'mesh_files': int(frames * 2),
            'motion': str(motion_path), 'state': str(state_path),
            'evidence': str(evidence_path), 'raw_trajectory': str(raw_path),
            'sha256': {str(path): _digest(path) for path in
                       (motion_path, state_path, pose_path, evidence_path, raw_path)},
            'physical_success_verified': False, 'body_stationary_verified': False,
            'phase_sync_verified': False}


def verify_artifacts(context, run_root):
    """Return a bounded verification report or a clean fatal runtime error."""
    try:
        return _verify_artifacts(context, run_root)
    except RuntimeFailure:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        raise RuntimeFailure('Malformed generated artifact: ' + type(error).__name__) from error
