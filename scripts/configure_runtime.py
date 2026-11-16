#!/usr/bin/env python3
"""Validate a private config against published hashes before enabling live use."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'trial_01'))
from launcher import settings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, help='Existing private config; default .local/runtime.json.')
    args = parser.parse_args(argv)
    if args.config:
        os.environ['INTERPOSE_LAB_CONFIG'] = str(args.config.expanduser().resolve())
    try:
        config = settings.load_config()
        manifest = settings.verify_expected(config)
        destination = settings.manifest_path()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix('.tmp')
        with temporary.open('w') as stream:
            json.dump(manifest, stream, indent=2); stream.write('\n')
        os.chmod(str(temporary), 0o600)
        os.replace(str(temporary), str(destination))
        print('Configuration and published hashes verified. Private runtime manifest written.')
        print('No credential was read; no API, simulator or model was executed.')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('Configuration failed: '+str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
