#!/usr/bin/env python3
"""Synthetic CPU waypoint validation only: no LLM, assets, simulator or motion generation."""
import argparse
import ast
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = ROOT/'trial_01/executor_code/protomotios_generate_multi_object.py'


def validator():
    path = ROOT/'trial_01/executor_code/waypoint_validation.py'
    spec = importlib.util.spec_from_file_location('offline_waypoint_validator', str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture():
    """Own synthetic coordinates, unrelated to licensed scene/body data."""
    goal = {'action':'lift_hold_return_release', 'object':'synthetic_box',
            'center_xyz_m':[0.4, 0., 0.5], 'lift_height_m':0.2,
            'hold_duration_s':5., 'release_after_placement':True,
            'settle_duration_s':1., 'hand_withdraw_duration_s':1.,
            'hand_withdraw_distance_m':0.1}
    plan = {'control_joints':['pelvis'], 'control_points':[[[0,0.,0.,1.],[210,0.,0.,1.]]],
            'text':'Synthetic box: lift, hold five seconds, return and release.',
            'number_frames':210, 'task_index':1, 'object_name':['synthetic_box'],
            'object_points':[[[0,0.4,0.,0.5], [30,0.4,0.,0.7],
                              [180,0.4,0.,0.7], [210,0.4,0.,0.5]]]}
    return goal, plan


def validate(plan, goal):
    helper = validator()
    helper.validate_motion_arguments(**plan)
    raw = helper.validate_lift_hold_waypoints(plan['object_name'], plan['object_points'],
                                            goal, goal['center_xyz_m'], plan['number_frames'])
    tree = ast.parse(EXECUTOR.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'protomotion_model')
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'adjust_frames')
    namespace = {'np':np}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(EXECUTOR), 'exec'), namespace)
    initial = np.zeros((24,3)); initial[0] = [0.,0.,1.]
    proxy = SimpleNamespace(preserve_object_waypoint_height=True, target_lift_height=1.2, check_collision=True)
    controls, points, count = namespace['adjust_frames'](proxy, copy.deepcopy(plan['control_points']),
                                                        copy.deepcopy(plan['object_points']), plan['number_frames'], initial)
    retimed = helper.validate_lift_hold_waypoints(plan['object_name'], points, goal,
                                                 goal['center_xyz_m'], count)
    return {'status':'SYNTHETIC_VALIDATION_PASS', 'source':'own_synthetic_fixture',
            'API_called':False, 'model_constructed':False, 'motion_generated':False,
            'physical_success_verified':False, 'raw_validation':raw, 'retimed_validation':retimed,
            'retimed_waypoints':points, 'number_frames':int(count)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'.local/offline_demo.json')
    args = parser.parse_args(argv)
    path = args.output.expanduser().resolve()
    if ROOT/'.local' not in path.parents:
        parser.error('Output must remain under this repository .local directory.')
    if path.exists():
        parser.error('Output already exists; choose a fresh filename.')
    goal, plan = fixture()
    result = validate(plan, goal)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print('SYNTHETIC_VALIDATION_PASS: actual waypoint validator and executor adjust_frames passed.')
    print('No motion generated; no API, SDK, model, credential or external checkout used.')
    print('Report: '+str(path))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
