"""Private runtime configuration and published, relocation-safe integrity guards."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = ('interpose_root', 'protomotions_root', 'interpose_python',
            'simulator_python', 'smplsim_root', 'isaacgym_python_root',
            'smplx_root', 'checkpoint', 'data_root', 'key_file')


def config_path():
    return Path(os.environ.get('INTERPOSE_LAB_CONFIG', str(ROOT/'.local/runtime.json'))).expanduser().resolve()


def manifest_path():
    return ROOT/'.local/runtime_manifest.json'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_config():
    try:
        config = json.loads(config_path().read_text())
    except (OSError, ValueError):
        raise ValueError('Private runtime configuration is missing/invalid; run scripts/configure_runtime.py.') from None
    if config.get('schema_version') != 1 or not isinstance(config.get('paths'), dict):
        raise ValueError('Runtime configuration requires schema_version=1 and paths.')
    if config.get('api', {}).get('model') != 'gpt-4o':
        raise ValueError('This validated planner contract requires api.model=gpt-4o.')
    for name in REQUIRED:
        value = config['paths'].get(name)
        if not isinstance(value, str) or not value:
            raise ValueError('Missing runtime path: '+name)
    for name, value in config['paths'].items():
        if not isinstance(value, str):
            raise ValueError('Runtime path must be a string: '+name)
        expanded = Path(value).expanduser()
        if not expanded.is_absolute():
            expanded = config_path().parent/expanded
        config['paths'][name] = str(expanded.absolute() if name == 'key_file' else expanded.resolve())
    return config


def _resolve_entry(config, entry):
    root = entry['root']
    if root not in ('repo', 'interpose_root', 'protomotions_root', 'checkpoint', 'checkpoint_config'):
        raise ValueError('Unknown published dependency root: '+str(root))
    if root == 'repo':
        base = ROOT
    elif root == 'checkpoint_config':
        checkpoint = Path(config['paths']['checkpoint'])
        base = checkpoint.parent/'config.yaml'
        if not base.is_file():
            base = checkpoint.parent.parent/'config.yaml'
    else:
        base = Path(config['paths'][root])
    relative = Path(entry['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Published manifest path must stay relative to its tagged root.')
    return base/relative


def verify_expected(config):
    """Check trusted published expectations; never accept new external hashes."""
    dependencies = json.loads((ROOT/'manifests/dependency_files.json').read_text())
    package = json.loads((ROOT/'manifests/package_files.json').read_text())
    entries = dependencies['entries']
    hashes = package['sha256']
    if not isinstance(entries, list) or not entries or not isinstance(hashes, dict) or not hashes:
        raise ValueError('Published dependency/package manifests must be nonempty.')
    for name in REQUIRED:
        if name != 'key_file' and not Path(config['paths'][name]).exists():
            raise ValueError('Required runtime path is missing: '+name)
    for entry in entries:
        path = _resolve_entry(config, entry)
        if not path.is_file() or digest(path) != entry['sha256']:
            raise ValueError('Published dependency hash mismatch: '+entry['root']+':'+entry['path'])
    for relative, expected in hashes.items():
        path = _resolve_entry(config, {'root':'repo', 'path':relative})
        if not path.is_file() or digest(path) != expected:
            raise ValueError('Published package hash mismatch: '+relative)
    return {'schema_version':1, 'config_sha256':digest(config_path()),
            'dependency_entries':entries, 'package_sha256':hashes}


def verify_runtime_manifest():
    config = load_config()
    try:
        local = json.loads(manifest_path().read_text())
    except (ValueError, OSError):
        raise ValueError('Private runtime manifest is missing/invalid; configure the verified runtime first.') from None
    expected = verify_expected(config)
    if local != expected:
        raise ValueError('Private runtime manifest differs from configuration/published expectations; reconfigure after reviewing changes.')
    return local
