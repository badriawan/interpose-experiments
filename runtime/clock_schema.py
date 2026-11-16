"""Validate single-environment, single-episode recorder clocks without a GPU."""
import math


def validate_clock_evidence(report):
    """Clocks validate recording convention, not physical body/object phase."""
    steps = report.get('clock_steps', [])
    records = report.get('clock_records', [])
    resets = report.get('reset_clocks', [])
    count = len(records)
    dt = float(report.get('env_dt', float('nan')))
    errors = []
    if not math.isfinite(dt) or dt <= 0:
        return {'status': 'FAIL', 'errors': ['invalid dt']}
    if not count or len(steps) != count or report.get('recorded_frames') != count or report.get('policy_calls') != count:
        errors.append('step/record/action/frame counts differ or are empty')
    if report.get('num_envs') != 1:
        errors.append('clock observer is scoped to one environment')
    if not resets:
        errors.append('reset clock missing')
    # Float32 reference clock accumulates dt; report the error and allow a small
    # duration-scaled numerical tolerance rather than demanding exact equality.
    cumulative_tolerance_s = max(1e-6, count * dt * 5e-6)
    increment_tolerance_s = 2e-6
    maximum_ref_error = maximum_sdk_error = maximum_pair_difference = 0.0
    try:
        reference_start = float(steps[0]['before']['motion_time_s'])
        sdk_start = float(steps[0]['before']['sdk_time_s'])
        if abs(reference_start) > cumulative_tolerance_s:
            errors.append('reference does not begin at zero for this evaluation')
        if resets and (abs(float(resets[-1]['motion_time_s']) - reference_start) > cumulative_tolerance_s or abs(float(resets[-1]['sdk_time_s']) - sdk_start) > cumulative_tolerance_s):
            errors.append('last reset does not match first pre-step clock')
        for i, (step, record) in enumerate(zip(steps, records)):
            values = [float(step[when][clock]) for when in ('before', 'after') for clock in ('motion_time_s', 'sdk_time_s')]
            values += [float(record[clock]) for clock in ('motion_time_s', 'sdk_time_s')]
            if not all(math.isfinite(v) for v in values):
                errors.append('nonfinite clock at record {}'.format(i))
                continue
            before_ref, before_sdk, after_ref, after_sdk, record_ref, record_sdk = values
            maximum_ref_error = max(maximum_ref_error, abs(before_ref - reference_start - i * dt), abs(after_ref - reference_start - (i + 1) * dt))
            maximum_sdk_error = max(maximum_sdk_error, abs(before_sdk - sdk_start - i * dt), abs(after_sdk - sdk_start - (i + 1) * dt))
            maximum_pair_difference = max(maximum_pair_difference, abs((record_ref-reference_start) - (record_sdk-sdk_start)))
            if abs(after_ref - before_ref - dt) > increment_tolerance_s or abs(after_sdk - before_sdk - dt) > increment_tolerance_s:
                errors.append('clock increment differs from dt at record {}'.format(i))
            if abs(record_ref - after_ref) > 1e-9 or abs(record_sdk - after_sdk) > 1e-9:
                errors.append('recorder clock differs from post-step clock at record {}'.format(i))
        if maximum_ref_error > cumulative_tolerance_s or maximum_sdk_error > cumulative_tolerance_s:
            errors.append('accumulated clock error exceeds tolerance')
        if maximum_pair_difference > cumulative_tolerance_s:
            errors.append('relative reference/SDK clock disagreement exceeds tolerance')
    except (KeyError, IndexError, TypeError, ValueError) as error:
        errors.append('malformed clock evidence: ' + type(error).__name__)
    return {'status': 'FAIL' if errors else 'PASS', 'errors': errors,
        'observed_records': count, 'dt_s': dt,
        'cumulative_tolerance_s': cumulative_tolerance_s,
        'max_reference_accumulation_error_s': maximum_ref_error,
        'max_sdk_accumulation_error_s': maximum_sdk_error,
        'max_relative_clock_disagreement_s': maximum_pair_difference,
        'recorder_convention': 'post-step reference/SDK clocks, environment index0',
        'object_clock_measured': False, 'physical_phase_sync_verified': False}
