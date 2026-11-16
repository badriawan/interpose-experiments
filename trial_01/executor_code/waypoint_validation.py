# Adapted from InterPose (Copyright 2025 Yangsong ZHANG) and local experiment code.
# InterPose MIT license: ../../third_party/InterPose-LICENSE.txt (repository third_party).
"""Pure CPU checks for the bounded lift/hold/return exercise, not physics."""
import numbers
import numpy as np

FPS = 30
FRAME_BUDGET = 900  # Existing bounded planner protocol, not a model-wide limit.
POSITION_TOLERANCE_M = 0.001
HEIGHT_TOLERANCE_M = 0.001
FLAT_TOLERANCE_M = 0.000001


class WaypointValidationError(ValueError):
    pass


def _fail(message):
    raise WaypointValidationError(message)


def _scalar(value, label, positive=False):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real):
        _fail(label + ' must be a real number, not a boolean or string.')
    try:
        value = float(value)
    except (OverflowError, ValueError):
        _fail(label + ' is outside the supported numeric range.')
    if not np.isfinite(value) or (positive and value <= 0):
        _fail(label + ' must be finite' + (' and positive.' if positive else '.'))
    return value


def _array(value, label):
    try:
        original = np.asarray(value, dtype=object)
    except (ValueError, TypeError):
        _fail(label + ' must be a rectangular numeric array.')
    if any(isinstance(x, (bool, np.bool_)) or not isinstance(x, numbers.Real) for x in original.flat):
        _fail(label + ' must contain only real numbers, not booleans or strings.')
    try:
        result = np.asarray(original, dtype=np.float64)
    except (ValueError, TypeError, OverflowError):
        _fail(label + ' is outside the supported numeric range.')
    if not np.isfinite(result).all():
        _fail(label + ' contains nonfinite values.')
    return result


def _vector(value, label):
    result = _array(value, label)
    if result.shape != (3,):
        _fail(label + ' must have exactly three coordinates.')
    return result


def _frame_count(value, label):
    value = _scalar(value, label)
    if value != round(value) or not 0 <= value <= FRAME_BUDGET:
        _fail(label + ' must be an integer in 0..900 for this bounded exercise.')
    return int(value)


def _group(value, label, horizon=FRAME_BUDGET, minimum=1):
    if isinstance(value, np.ndarray) and value.ndim == 0:
        _fail(label + ' must be a waypoint sequence.')
    if not isinstance(value, (list, tuple, np.ndarray)) or not minimum <= len(value) <= FRAME_BUDGET + 1:
        _fail(label + ' has an invalid waypoint count.')
    result = _array(value, label)
    if result.ndim != 2 or result.shape[1] != 4:
        _fail(label + ' must have shape [waypoint,4] with rows [frame,x,y,z].')
    frames = result[:, 0]
    if (frames < 0).any() or (frames > horizon).any() or (frames != np.rint(frames)).any():
        _fail(label + ' requires nonnegative integer frames within number_frames.')
    if (np.diff(frames) <= 0).any():
        _fail(label + ' frames must be strictly increasing without duplicates.')
    return result


def validate_motion_arguments(control_joints, control_points, text, number_frames,
                              task_index, object_name, object_points):
    """Reject malformed calls before legacy code indexes or reshapes them."""
    if isinstance(number_frames, (bool, np.bool_)) or not isinstance(number_frames, (int, np.integer)):
        _fail('number_frames must be an integer argument.')
    if isinstance(task_index, (bool, np.bool_)) or not isinstance(task_index, (int, np.integer)):
        _fail('task_index must be an integer argument.')
    horizon = _frame_count(number_frames, 'number_frames')
    if horizon <= 30:
        _fail('number_frames must exceed 30.')
    index = _frame_count(task_index, 'task_index')
    if not 1 <= index <= 10:
        _fail('task_index must be in 1..10.')
    if not isinstance(text, str) or not text.strip():
        _fail('text must be a nonempty task description.')
    if not isinstance(control_joints, list) or not control_joints:
        _fail('control_joints must be a nonempty list.')
    if any(not isinstance(j, str) or j not in ('pelvis', 'left_hand', 'right_hand') for j in control_joints):
        _fail('Unsupported control joint.')
    if len(set(control_joints)) != len(control_joints):
        _fail('Control joints must not be duplicated.')
    if not isinstance(control_points, (list, tuple)) or len(control_points) != len(control_joints):
        _fail('control_points must match control_joints.')
    for i, group in enumerate(control_points):
        _group(group, 'control_points[' + str(i) + ']', horizon)
    names = [object_name] if isinstance(object_name, str) else object_name
    if names is None or (isinstance(names, list) and not names):
        if object_points is not None and not (isinstance(object_points, (list, tuple)) and not object_points):
            _fail('Object points require object names.')
        return
    if not isinstance(names, list) or any(not isinstance(n, str) or not n for n in names):
        _fail('object_name must contain nonempty strings.')
    if len(set(names)) != len(names):
        _fail('Object names must not be duplicated.')
    if not isinstance(object_points, (list, tuple)) or len(object_points) != len(names):
        _fail('object_points must match object_name.')
    for i, group in enumerate(object_points):
        _group(group, 'object_points[' + str(i) + ']', horizon, minimum=2)


def validate_lift_goal(goal):
    if not isinstance(goal, dict) or not isinstance(goal.get('action'), str) or goal.get('action') != 'lift_hold_return_release':
        _fail('custom_goal.action must be lift_hold_return_release.')
    required = ('object', 'center_xyz_m', 'lift_height_m', 'hold_duration_s',
                'release_after_placement', 'settle_duration_s',
                'hand_withdraw_duration_s', 'hand_withdraw_distance_m')
    if any(k not in goal for k in required):
        _fail('custom_goal is missing required lift/hold/release fields.')
    if not isinstance(goal['object'], str) or not goal['object']:
        _fail('custom_goal.object must be a nonempty object name.')
    _vector(goal['center_xyz_m'], 'center_xyz_m')
    lift = _scalar(goal['lift_height_m'], 'lift_height_m', positive=True)
    if lift <= 2 * HEIGHT_TOLERANCE_M:
        _fail('lift_height_m is too small for the 1mm validation tolerance.')
    if lift > FRAME_BUDGET * 0.04:
        _fail('lift_height_m exceeds the frame-budget/0.04m-per-step bound; this is not a reachability guarantee.')
    if goal['release_after_placement'] is not True:
        _fail('This action requires release_after_placement=true.')
    frames = {}
    for key in ('hold_duration_s', 'settle_duration_s', 'hand_withdraw_duration_s'):
        seconds = _scalar(goal[key], key, positive=True)
        if seconds > FRAME_BUDGET / FPS:
            _fail(key + ' exceeds the bounded exercise duration budget.')
        count = seconds * FPS
        if abs(count - round(count)) > 1e-6 or not 1 <= round(count) <= FRAME_BUDGET:
            _fail(key + ' must be a positive whole number of intervals at 30Hz within the frame budget.')
        frames[key] = int(round(count))
    _scalar(goal['hand_withdraw_distance_m'], 'hand_withdraw_distance_m', positive=True)
    if 'endpoint_position_tolerance_m' in goal:
        _scalar(goal['endpoint_position_tolerance_m'], 'endpoint_position_tolerance_m', positive=True)
    return frames


def validate_lift_hold_waypoints(object_name, object_points, goal, initial_center, number_frames=None):
    """Validate one monotone rise, exact requested plateau and return; no edits."""
    durations = validate_lift_goal(goal)
    initial = _vector(initial_center, 'initial_center')
    requested_end = _vector(goal['center_xyz_m'], 'center_xyz_m')
    names = [object_name] if isinstance(object_name, str) else object_name
    if not isinstance(names, list) or len(names) != 1 or not isinstance(names[0], str) or names[0] != goal['object']:
        _fail('Use exactly the requested object: ' + goal['object'] + '.')
    if not isinstance(object_points, (list, tuple)) or len(object_points) != 1:
        _fail('Exactly one object waypoint group is required.')
    horizon = FRAME_BUDGET if number_frames is None else _frame_count(number_frames, 'number_frames')
    points = _group(object_points[0], 'object_points[0]', horizon, minimum=3)
    virtual_initial = points[0, 0] > 0
    if virtual_initial:
        points = np.vstack((np.r_[0, initial], points))
    if np.linalg.norm(points[0, 1:] - initial) > POSITION_TOLERANCE_M:
        _fail('Frame0 must match the known initial object center within 1mm.')
    if np.linalg.norm(requested_end - initial) > POSITION_TOLERANCE_M:
        _fail('This stationary exercise must return to its known initial center within 1mm.')
    if np.linalg.norm(points[-1, 1:] - requested_end) > POSITION_TOLERANCE_M:
        _fail('Final object center must match custom_goal.center_xyz_m within 1mm.')
    if (np.linalg.norm(points[:, 1:3] - initial[:2], axis=1) > POSITION_TOLERANCE_M).any():
        _fail('Keep object X/Y fixed within 1mm; this exercise has no horizontal carry.')
    z = points[:, 3]
    requested_peak = initial[2] + float(goal['lift_height_m'])
    if z.min() < initial[2] - HEIGHT_TOLERANCE_M or abs(z.max() - requested_peak) > HEIGHT_TOLERANCE_M:
        _fail('Object peak must be initial Z + lift_height_m within 1mm, with no drop below baseline.')
    plateau = np.flatnonzero(np.abs(z - z.max()) <= FLAT_TOLERANCE_M)
    if len(plateau) < 2 or (np.diff(plateau) != 1).any():
        _fail('Provide one contiguous constant-height hold with at least two peak waypoints.')
    first, last = int(plateau[0]), int(plateau[-1])
    if first == 0 or last == len(points) - 1:
        _fail('Include a rise before the hold and a return after it.')
    if (np.diff(z[:first + 1]) < -FLAT_TOLERANCE_M).any() or (np.diff(z[last:]) > FLAT_TOLERANCE_M).any():
        _fail('Use one monotone rise, one hold, then one monotone descent; no dips or re-lifts.')
    hold_frames = int(points[last, 0] - points[first, 0])
    required_hold = durations['hold_duration_s']
    if hold_frames != required_hold:
        _fail('Hold must span exactly ' + str(required_hold) + ' intervals at 30Hz; received ' + str(hold_frames) + '.')
    tail_frames = durations['settle_duration_s'] + durations['hand_withdraw_duration_s']
    if points[-1, 0] + tail_frames > FRAME_BUDGET:
        _fail('Object plan plus settle/withdraw tail exceeds this exercise budget of 900 intervals.')
    return {'status': 'PASS', 'fps': FPS, 'hold_intervals': hold_frames,
            'hold_start_frame': int(points[first, 0]), 'hold_end_frame': int(points[last, 0]),
            'placement_frame': int(points[-1, 0]), 'peak_center_z_m': float(z.max()),
            'lift_from_known_initial_m': float(z.max() - initial[2]),
            'virtual_known_frame0_for_validation': bool(virtual_initial),
            'waypoint_position_tolerance_m': POSITION_TOLERANCE_M,
            'waypoint_height_tolerance_m': HEIGHT_TOLERANCE_M,
            'plateau_flat_tolerance_m': FLAT_TOLERANCE_M,
            'scope': 'planned object waypoints only; body/physical success unverified'}
