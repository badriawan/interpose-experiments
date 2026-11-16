# Adapted from InterPose (Copyright 2025 Yangsong ZHANG) and local experiment code.
# InterPose MIT license: ../../third_party/InterPose-LICENSE.txt (repository third_party).
"""Safe default: CPU preflight. --execute is reserved for an explicit real run."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from launcher import core


def main(argv=None):
    p=argparse.ArgumentParser(description='InterPose trial: prompt → LLM plan → validation → one interaction.')
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--preflight',action='store_true',help='Check inputs/assets without credentials, API or model (default).')
    modes.add_argument('--dry-run',action='store_true',help='Validate a synthetic planner fixture using configured local assets; no API/model.')
    modes.add_argument('--execute',action='store_true',help='Run one real API and simulator interaction after preparation passes.')
    modes.add_argument('--prepare-recovery',action='store_true',help='Validate a saved planner response without API/key/model.')
    modes.add_argument('--resume-saved-plan',action='store_true',help='Resume a recovered saved plan using GPU/simulator without a new API call.')
    p.add_argument('--data-folder',type=Path,help='Scene folder containing environment_state and motion_data.')
    p.add_argument('--scenario',default=core.DEFAULT_SCENARIO)
    p.add_argument('--run-name',help='New run directory name for execution/recovery.')
    p.add_argument('--report',type=Path,help='Save a new inspection report inside the trial directory.')
    args=p.parse_args(argv)
    if args.run_name and not (args.execute or args.prepare_recovery or args.resume_saved_plan):p.error('--run-name requires an execution/recovery mode')
    if (args.prepare_recovery or args.resume_saved_plan) and not args.run_name:p.error('Recovery requires --run-name')
    if (args.prepare_recovery or args.resume_saved_plan) and args.data_folder:p.error('Recovery uses the original run input snapshots; do not supply --data-folder')
    try:
        if args.report:
            report_path=args.report.resolve()
            if core.BASE not in report_path.parents:raise core.InputError('Report must remain within the exercise folder.')
            if report_path.exists():raise core.InputError('Report already exists; choose a new report filename.')
        if args.prepare_recovery:
            from launcher import recovery
            result=recovery.prepare_saved_plan(args.run_name)
        elif args.resume_saved_plan:
            from launcher import recovery
            root,result=recovery.resume_saved_plan(args.run_name)
            result={'status':result['status'],'run_directory':str(root),'status_manifest':str(root/'resume_manifest.json'),'API_calls':0,'physical_success_verified':False}
        elif args.execute:
            ctx=core.preflight(args.data_folder,args.scenario)
            root,result=core.execute(ctx,args.run_name)
            result={'status':result['status'],'run_directory':str(root),'physical_success_verified':False}
        else:
            ctx=core.preflight(args.data_folder,args.scenario)
            result=core.dry_run(ctx) if args.dry_run else {'status':'PREFLIGHT_PASS','context':core.public_context(ctx),'API_called':False,'model_constructed':False}
        if args.report:core.write_json(args.report.resolve(),result,exclusive=True)
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except KeyboardInterrupt:
        print('INTERRUPTED: partial outputs retained.',file=sys.stderr);return 130
    except (core.LaunchError,OSError,ValueError,KeyError) as e:
        print(core.redact(type(e).__name__+': '+str(e)),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
