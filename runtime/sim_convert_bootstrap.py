"""Pinned official converter with a private XML temporary directory.

The sole AST substitution changes TMP_SMPL_DIR, preserving motion math.
The source is verified against the published dependency hash first.
"""
import ast
import ipaddress
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'trial_01'))
from launcher import settings
CONFIG = settings.load_config()
settings.verify_runtime_manifest()
ROOT = Path(CONFIG['paths']['protomotions_root'])


def private_temporary_directory(tree, destination):
    matches = [node for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == 'TMP_SMPL_DIR' for target in node.targets)]
    if len(matches) != 1 or not isinstance(matches[0].value, ast.Constant) or matches[0].value.value != '/tmp/smpl':
        raise RuntimeError('Pinned converter TMP_SMPL_DIR contract changed.')
    matches[0].value = ast.copy_location(ast.Constant(value=str(destination)), matches[0].value)
    return ast.fix_missing_locations(tree)


def local_only(event, args):
    if event != 'socket.connect' or not isinstance(args[1], tuple):
        return
    host = str(args[1][0])
    local = host in ('localhost', '127.0.0.1', '::1')
    try:
        local = local or ipaddress.ip_address(host).is_loopback
    except ValueError:
        pass
    if not local:
        raise RuntimeError('External network disabled in conversion child.')


def main():
    for key in list(os.environ):
        if key.startswith(('OPENAI_', 'AZURE_OPENAI_', 'ANTHROPIC_', 'GEMINI_', 'MISTRAL_', 'COHERE_')) or key in ('GOOGLE_API_KEY', 'INTERPOSE_API_KEY_FILE'):
            os.environ.pop(key, None)
    sys.addaudithook(local_only)
    temporary = settings.ROOT/'.local/tmp/smpl'
    temporary.mkdir(parents=True, exist_ok=True)
    for path in (ROOT, ROOT/'data/scripts', Path(CONFIG['paths']['smplsim_root']), Path(CONFIG['paths']['isaacgym_python_root'])):
        sys.path.insert(0, str(path))
    source = ROOT/'data/scripts/convert_amass_to_isaac.py'
    tree = private_temporary_directory(ast.parse(source.read_text()), temporary)
    sys.argv[0] = str(source)
    exec(compile(tree, str(source), 'exec'), {'__name__':'__main__', '__file__':str(source), '__package__':None})


if __name__ == '__main__':
    main()
