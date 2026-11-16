#!/usr/bin/env python3
"""Verify local package code hashes; --write explicitly updates them after review."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Record reviewed package code, not external dependency hashes.')
    args = parser.parse_args()
    files = [p for folder in ('trial_01','runtime','scripts') for p in (ROOT/folder).rglob('*')
             if p.is_file() and p.suffix in ('.py','.sh') and 'runs' not in p.relative_to(ROOT).parts and '__pycache__' not in p.parts]
    expected = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    target=ROOT/'manifests/package_files.json'
    if args.write:
        target.write_text(json.dumps({'schema_version':1,'sha256':expected},indent=2)+'\n')
        print('Recorded {} package code files. Reconfigure the private runtime after review.'.format(len(expected)))
    elif target.exists() and json.loads(target.read_text()).get('sha256')==expected:
        print('Package manifest PASS: {} files.'.format(len(expected)))
    else:
        raise SystemExit('Package manifest FAIL: code files changed; review before --write.')


if __name__=='__main__':
    main()
