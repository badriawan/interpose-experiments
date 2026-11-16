#!/usr/bin/env python3
"""List pinned sources by default; --fetch prepares new ignored external checkouts."""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    commit: str
    patch: str = ''


SOURCES = (
    Source('InterPose', 'https://github.com/Mael-zys/InterPose.git', '5ee373310a75fa15719959b2808f8d399f27ae16', 'InterPose.patch'),
    Source('ProtoMotion_for_InterPose', 'https://github.com/Mael-zys/ProtoMotion_for_InterPose.git', 'ad70a3785bf162c89a8df91eb79568770416f1d8', 'ProtoMotion_isaacgym.patch'),
    Source('vendor/SMPLSim', 'https://github.com/ZhengyiLuo/SMPLSim.git', 'b5c08720503ad5fff64050c4d289c42d947fcf8d'),
    Source('vendor/smplx', 'https://github.com/ZhengyiLuo/smplx.git', 'a5b8e4ac14f79f3f33fd2cf2a16e6f507146b813'),
    Source('vendor/human_body_prior', 'https://github.com/nghorbani/human_body_prior.git', '4c246d8a83ce16d3cff9c79dcf04d81fa440a6bc'),
    Source('vendor/bps_torch', 'https://github.com/otaheri/bps_torch.git', '00fcac3dffd294211d4ea0363eaf6c2ca4e068dc'),
    Source('vendor/chamfer_distance', 'https://github.com/otaheri/chamfer_distance.git', 'f86f6f7cadd3aca642704573d1626c67ca2e2846'),
)


class PreparationError(RuntimeError):
    pass


def git(args, cwd=None, env=None, check=True):
    environment = dict(os.environ)
    environment['GIT_LFS_SKIP_SMUDGE'] = '1'
    environment['GIT_TERMINAL_PROMPT'] = '0'
    if env:
        environment.update(env)
    result = subprocess.run(['git']+list(args), cwd=str(cwd) if cwd else None,
                            env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True)
    if check and result.returncode:
        raise PreparationError('git '+args[0]+' failed: '+result.stderr.strip())
    return result


def _verify_checkout(source, destination):
    # Refuse a directory inherited from some parent repository or a nested path.
    top = git(['rev-parse', '--show-toplevel'], destination).stdout.strip()
    if Path(top).resolve() != destination.resolve():
        raise PreparationError('Existing directory is not the requested checkout root: '+str(destination))
    if git(['rev-parse', 'HEAD'], destination).stdout.strip() != source.commit:
        raise PreparationError('Existing checkout has a different commit; it will not be reset: '+source.name)
    if git(['remote', 'get-url', 'origin'], destination).stdout.strip() != source.url:
        raise PreparationError('Existing checkout origin differs: '+source.name)
    if git(['symbolic-ref', '-q', 'HEAD'], destination, check=False).returncode == 0:
        raise PreparationError('Existing checkout is not detached; it will not be changed: '+source.name)
    if git(['diff', '--cached', '--quiet'], destination, check=False).returncode:
        raise PreparationError('Existing checkout has staged changes: '+source.name)


def _reject_untracked(destination, allowed=()):
    untracked = set(git(['ls-files', '--others', '--exclude-standard', '-z'], destination).stdout.split('\0'))-{''}
    if untracked-set(allowed):
        raise PreparationError('Existing checkout contains unrelated untracked files: '+str(destination))


def _apply_or_verify_patch(destination, patch):
    if patch is None:
        _reject_untracked(destination)
        if git(['diff', '--quiet'], destination, check=False).returncode:
            raise PreparationError('Existing checkout is dirty; no changes were made: '+str(destination))
        return 'not_required'
    patch = Path(patch).resolve()
    if not patch.is_file() or not patch.stat().st_size:
        raise PreparationError('Required package patch is missing/empty: '+patch.name)
    # Build the exact allowed tracked state in a temporary index, without
    # touching the real index or working tree. Reverse-check alone would allow
    # unrelated dirty edits; exact tree comparison prevents that.
    scratch = ROOT/'.local/tmp'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='interpose-patch-', dir=str(scratch)) as temp:
        environment = {'GIT_INDEX_FILE':str(Path(temp)/'index')}
        git(['read-tree', 'HEAD'], destination, environment)
        git(['apply', '--cached', str(patch)], destination, environment)
        expected_tree = git(['write-tree'], destination, environment).stdout.strip()
        additions = set(git(['diff-tree', '--no-commit-id', '--name-only', '--diff-filter=A', '-r', '-z', 'HEAD', expected_tree], destination).stdout.split('\0'))-{''}
        _reject_untracked(destination, additions)
        # The temporary index tracks patch additions too. Comparing it directly
        # to the working tree checks their contents/mode without staging them.
        exact_applied = git(['diff', '--quiet', '--'], destination, environment, check=False).returncode == 0
    clean = git(['diff', '--quiet'], destination, check=False).returncode == 0
    if exact_applied:
        git(['apply', '--reverse', '--check', str(patch)], destination)
        return 'already_applied'
    if not clean:
        raise PreparationError('Existing checkout has unrelated/partial changes; refusing to patch: '+str(destination))
    git(['apply', '--check', str(patch)], destination)
    git(['apply', str(patch)], destination)
    return 'applied'


def _verify_submodules(destination):
    if not (destination/'.gitmodules').is_file():
        return
    status = git(['submodule', 'status', '--recursive'], destination).stdout
    if any(line and line[0] in '-+U' for line in status.splitlines()):
        raise PreparationError('Existing official submodules are missing or at incompatible commits; checkout preserved.')
    # No update/reset of existing directories, even when a submodule is dirty.
    script = 'test -z "$(git status --porcelain)" || exit 1'
    git(['submodule', 'foreach', '--recursive', script], destination)


def prepare_source(source, destination, patch=None):
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_dir():
            raise PreparationError('Existing destination is not a regular checkout directory: '+str(destination))
        _verify_checkout(source, destination)
        _verify_submodules(destination)
        state = _apply_or_verify_patch(destination, patch)
        return {'source':source.name, 'commit':source.commit, 'status':'existing_verified', 'patch':state}
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name('.'+destination.name+'.preparing-'+uuid.uuid4().hex)
    try:
        git(['clone', '--no-checkout', source.url, str(temporary)])
        git(['checkout', '--detach', source.commit], temporary)
        if git(['rev-parse', 'HEAD'], temporary).stdout.strip() != source.commit:
            raise PreparationError('Pinned checkout verification failed: '+source.name)
        if (temporary/'.gitmodules').is_file():
            git(['submodule', 'update', '--init', '--recursive'], temporary)
        _verify_checkout(source, temporary)
        _verify_submodules(temporary)
        state = _apply_or_verify_patch(temporary, patch)
        if destination.exists() or destination.is_symlink():
            raise PreparationError('Destination appeared while cloning; refusing overwrite.')
        temporary.rename(destination)
        return {'source':source.name, 'commit':source.commit, 'status':'new_checkout', 'patch':state}
    except BaseException as error:
        raise PreparationError(str(error)+'; incomplete new checkout preserved at '+str(temporary)) from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='Explicitly clone pinned sources under external/ and apply package patches.')
    args = parser.parse_args(argv)
    if not args.fetch:
        print(json.dumps({'mode':'list_only_no_network', 'sources':[source.__dict__ for source in SOURCES]}, indent=2))
        print('No installation, SDK, data or model download is performed. LFS smudging is disabled during fetch.')
        return 0
    try:
        # Fail before any network access when the package is incomplete.
        for source in SOURCES:
            if source.patch and not (ROOT/'patches'/source.patch).is_file():
                raise PreparationError('Missing package patch: '+source.patch)
        for parent in (ROOT/'external', ROOT/'external/vendor'):
            if parent.is_symlink():
                raise PreparationError('External source parent must not be a symlink: '+str(parent))
        for source in SOURCES:
            patch = ROOT/'patches'/source.patch if source.patch else None
            print(json.dumps(prepare_source(source, ROOT/'external'/source.name, patch)), flush=True)
        return 0
    except (PreparationError, OSError) as error:
        print('Source preparation failed: '+str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
