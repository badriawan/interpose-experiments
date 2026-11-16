# Adapted from InterPose (Copyright 2025 Yangsong ZHANG) and local experiment code.
# InterPose MIT license: ../../third_party/InterPose-LICENSE.txt (repository third_party).
"""Narrow recovery of saved planner proposals; no key or API use in this module."""
import copy
from datetime import datetime
import json
from pathlib import Path
import re
from . import core


def _root(run_name):
    if not isinstance(run_name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',run_name):
        raise core.InputError('A valid existing run name is required.')
    root=(core.RUNS_ROOT/run_name).resolve()
    if core.BASE not in root.parents or not root.is_dir():raise core.InputError('Existing run is missing or outside the exercise folder.')
    return root


def _eligible(root):
    try:manifest=json.loads((root/'manifest.json').read_text())
    except (OSError,ValueError):raise core.InputError('Original failed run manifest is missing/invalid.') from None
    if manifest.get('status')!='FAILED' or manifest.get('error_type')!='PlanError' or manifest.get('dispatch_count')!=0:
        raise core.InputError('Saved-plan recovery requires FAILED/PlanError with dispatch_count=0.')
    for name in ('output','runtime_dispatch_started.json','resume_plan_claim.json','resume_manifest.json','accepted_plan.json'):
        if (root/name).exists():raise core.InputError('Run already has output/dispatch/resume evidence; no second dispatch is permitted: '+name)
    return manifest


def _snapshot_context(root,old):
    try:
        original=old['context'];scene=original['scene_name'];scenario=original['scenario']
        if Path(scene).name!=scene:raise ValueError('Invalid scene basename')
        ctx=core.preflight(root/'inputs'/scene,scenario)
        for role in ('input_json','input_motion'):
            expected=original['input_sha256'][original[role]]
            if core.digest(ctx[role])!=expected:raise core.InputError('Original input snapshot changed: '+role)
    except (KeyError,TypeError,ValueError):raise core.InputError('Original run context is incomplete or invalid.') from None
    return ctx


def _unique_interpretation(ctx,plan,legacy):
    candidates=[('frame_xyz',copy.deepcopy(plan))]
    if legacy:
        permuted=copy.deepcopy(plan)
        for field in ('control_points','object_points'):
            permuted[field]=[[[row[3],row[0],row[1],row[2]] for row in group] for group in plan[field]]
        candidates.append(('xyz_frame_to_frame_xyz',permuted))
    accepted=[];diagnostics=[]
    for label,candidate in candidates:
        try:validation=core.validate_plan(ctx,candidate)
        except core.PlanError as e:diagnostics.append({'layout':label,'status':'REJECTED','reason':str(e)})
        else:
            accepted.append((label,candidate,validation))
            diagnostics.append({'layout':label,'status':'VALIDATED','validation':validation})
    if len(accepted)!=1:
        raise core.PlanError('Saved proposal has '+str(len(accepted))+' valid layout interpretations; recovery requires exactly one.')
    return accepted[0],diagnostics


def prepare_saved_plan(run_name):
    root=_root(run_name);old=_eligible(root)
    if (root/'recovery').exists():raise core.InputError('Recovery evidence already exists; preserve it instead of overwriting.')
    original_hash=core.digest(root/'manifest.json')
    ctx=_snapshot_context(root,old)
    records=[];valid=[];source_hashes={}
    files=sorted((root/'planner').glob('attempt_[0-9][0-9]_planner_response.json'))
    for path in files:
        source_hashes[str(path)]=core.digest(path)
        try:
            stored=json.loads(path.read_text());response=stored['response']
            plan=core.parse_proposal(response,allow_legacy=True)
            raw=json.loads(response['message']['tool_calls'][0]['function']['arguments'],object_pairs_hook=core._unique_json_object)
            legacy=isinstance(raw['object_points'][0][0],list)
            choice,layouts=_unique_interpretation(ctx,plan,legacy)
        except (core.PlanError,KeyError,TypeError,ValueError) as e:
            records.append({'source':str(path),'status':'REJECTED','reason':str(e)})
        else:
            label,normalized,validation=choice
            record={'source':str(path),'status':'VALIDATED','layout':label,'layout_checks':layouts,'validation':validation}
            records.append(record);valid.append((path,label,normalized,validation))
    if not valid:raise core.PlanError('No saved proposal has an unambiguous valid interpretation; no API/model call was made.')
    # Deterministic selection: latest valid saved attempt, not a shortest/fastest plan.
    selected,label,plan,validation=valid[-1]
    _eligible(root)
    if core.digest(root/'manifest.json')!=original_hash:raise core.InputError('Original run manifest changed during recovery preparation.')
    if any(core.digest(p)!=h for p,h in source_hashes.items()):raise core.InputError('Saved response changed during recovery preparation.')
    folder=root/'recovery';folder.mkdir(exist_ok=False)
    with (folder/'original_failed_manifest.json').open('xb') as f:f.write((root/'manifest.json').read_bytes())
    core.write_json(folder/'recovered_plan.json',{'arguments':plan,'validation':validation},exclusive=True)
    report={'status':'RECOVERY_PREPARED','prepared_at':datetime.now().astimezone().isoformat(),
            'original_failed_manifest_sha256':original_hash,
            'source_response_sha256':source_hashes,'selected_response':str(selected),
            'selected_layout':label,'selection_rule':'latest_valid_saved_attempt',
            'transformation':'row permutation only; no coordinate, time, text or waypoint values invented',
            'candidates':records,'recovered_plan_sha256':core.digest(folder/'recovered_plan.json'),
            'old_runtime_manifest_sha256':old['context']['runtime_manifest_sha256'],
            'current_runtime_manifest_sha256':ctx['runtime_manifest_sha256'],
            'snapshot_sha256':{ctx[k]:core.digest(ctx[k]) for k in ('input_json','input_motion')},
            'API_calls':0,'credential_file_read':False,'model_constructed':False,'motion_generated':False}
    core.write_json(folder/'recovery_report.json',report,exclusive=True)
    return report


def validate_prepared_recovery(run_name):
    root=_root(run_name);old=_eligible(root);folder=root/'recovery'
    try:report=json.loads((folder/'recovery_report.json').read_text())
    except (OSError,ValueError):raise core.InputError('Prepare and review recovery evidence before resuming.') from None
    if report.get('status')!='RECOVERY_PREPARED':raise core.InputError('Recovery report is not prepared.')
    original_hash=report['original_failed_manifest_sha256']
    if core.digest(root/'manifest.json')!=original_hash or core.digest(folder/'original_failed_manifest.json')!=original_hash:
        raise core.InputError('Original failed manifest or its preserved copy changed.')
    for p,digest in report['source_response_sha256'].items():
        if Path(p).parent.resolve()!=(root/'planner').resolve() or core.digest(p)!=digest:
            raise core.InputError('Saved planner response changed after preparation.')
    if core.digest(folder/'recovered_plan.json')!=report['recovered_plan_sha256']:
        raise core.InputError('Recovered plan changed after preparation.')
    ctx=_snapshot_context(root,old)
    if ctx['runtime_manifest_sha256']!=report['current_runtime_manifest_sha256']:
        raise core.InputError('Current runtime version differs from reviewed recovery version.')
    for p,digest in report['snapshot_sha256'].items():
        if Path(p).resolve() not in (Path(ctx['input_json']).resolve(),Path(ctx['input_motion']).resolve()) or core.digest(p)!=digest:
            raise core.InputError('Input snapshot changed after preparation.')
    stored=json.loads((folder/'recovered_plan.json').read_text());plan=stored['arguments']
    validation=core.validate_plan(ctx,plan)
    # Verify the saved normalized plan is exactly derived from the chosen source.
    selected=Path(report['selected_response'])
    if str(selected) not in report['source_response_sha256']:raise core.InputError('Selected source is not in preserved response evidence.')
    saved=json.loads(selected.read_text())['response']
    original=core.parse_proposal(saved,allow_legacy=True)
    raw=json.loads(saved['message']['tool_calls'][0]['function']['arguments'])
    (layout,derived,_),_= _unique_interpretation(ctx,original,isinstance(raw['object_points'][0][0],list))
    if layout!=report['selected_layout'] or derived!=plan:
        raise core.InputError('Recovered arguments do not match the unambiguous saved-source interpretation.')
    return root,ctx,report,plan,validation


def resume_saved_plan(run_name,dispatch=None,verify=None):
    root,ctx,report,plan,validation=validate_prepared_recovery(run_name)
    _eligible(root)
    claim={'claimed_at':datetime.now().astimezone().isoformat(),
           'recovery_report_sha256':core.digest(root/'recovery/recovery_report.json'),
           'recovered_plan_sha256':report['recovered_plan_sha256'],
           'current_runtime_manifest_sha256':ctx['runtime_manifest_sha256']}
    # Exclusive creation is the single-dispatch boundary; a failed claim is never reused.
    try:
        with (root/'resume_plan_claim.json').open('x') as f:f.write(json.dumps(claim,indent=2)+'\n')
    except FileExistsError:raise core.InputError('Saved-plan resume has already been claimed; no second dispatch.') from None
    manifest={'status':'PLAN_RECOVERED','started_at':datetime.now().astimezone().isoformat(),
              'source_failed_manifest_sha256':report['original_failed_manifest_sha256'],
              'selected_response':report['selected_response'],'validation':validation,
              'dispatch_count':0,'API_calls':0,'credential_file_read':False,'physical_success_verified':False,
              'execution_mode':'INJECTED_DEPENDENCIES' if dispatch is not None or verify is not None else 'SAVED_PLAN_MODEL_AND_SIMULATOR'}
    core.write_json(root/'resume_manifest.json',manifest,exclusive=True)
    try:
        core.verify_runtime_manifest()
        if core.digest(core.manifest_path())!=ctx['runtime_manifest_sha256']:
            raise core.InputError('Runtime manifest changed after resume claim.')
        if dispatch is None or verify is None:
            from . import runtime
            dispatch=dispatch or runtime.dispatch;verify=verify or runtime.verify_artifacts
        manifest.update(status='DISPATCH_STARTED',dispatch_count=1)
        core.write_json(root/'resume_manifest.json',manifest)
        returned=dispatch(ctx,root,copy.deepcopy(plan))
        if returned is not None:raise core.LaunchError('Saved-plan executor did not finish: '+str(returned))
        artifacts=verify(ctx,root)
        manifest.update(status='ARTIFACTS_VERIFIED',artifacts=artifacts,completed_at=datetime.now().astimezone().isoformat())
        core.write_json(root/'resume_manifest.json',manifest)
        return root,manifest
    except BaseException as e:
        manifest.update(status='INTERRUPTED' if isinstance(e,KeyboardInterrupt) else 'FAILED',
                        error_type=type(e).__name__,error=core.redact(str(e)),completed_at=datetime.now().astimezone().isoformat())
        core.write_json(root/'resume_manifest.json',manifest)
        if isinstance(e,KeyboardInterrupt):raise
        raise core.LaunchError(core.redact(str(e))+'; preserved saved-plan resume '+str(root)) from None
