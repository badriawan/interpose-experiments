"""Launch a configured simulator Python without installing environments."""
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'trial_01'))
from launcher import settings


def main():
    config = settings.load_config()
    settings.verify_runtime_manifest()
    paths = config['paths']
    if len(sys.argv) < 2:
        raise SystemExit('A packaged simulator bootstrap is required.')
    script = Path(sys.argv[1]).resolve()
    if script not in (HERE/'sim_convert_bootstrap.py', HERE/'sim_eval_bootstrap.py'):
        raise SystemExit('Only packaged simulator bootstraps are supported.')
    python = Path(paths['simulator_python'])
    prefix = python.parent.parent
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith(('OPENAI_', 'AZURE_OPENAI_', 'ANTHROPIC_', 'GEMINI_',
                            'MISTRAL_', 'COHERE_')) or name in ('GOOGLE_API_KEY', 'INTERPOSE_API_KEY_FILE'):
            environment.pop(name, None)
    private = settings.ROOT/'.local'
    cache = private/'cache/torch_extensions'
    temporary = private/'tmp'
    cache.mkdir(parents=True, exist_ok=True)
    temporary.mkdir(parents=True, exist_ok=True)
    environment.update(INTERPOSE_LAB_CONFIG=str(settings.config_path()),
        LD_LIBRARY_PATH=str(prefix/'lib')+(':'+environment['LD_LIBRARY_PATH'] if environment.get('LD_LIBRARY_PATH') else ''),
        CPLUS_INCLUDE_PATH=str(prefix/'include'), TORCH_EXTENSIONS_DIR=str(cache),
        TMPDIR=str(temporary), MAX_JOBS='2', MPLBACKEND='Agg',
        WANDB_MODE='disabled', WANDB_DISABLED='true', HF_HUB_OFFLINE='1',
        TRANSFORMERS_OFFLINE='1', HYDRA_FULL_ERROR='1')
    compiler = paths.get('cxx')
    if compiler:
        if not Path(compiler).is_file():
            raise SystemExit('Configured compiler is missing.')
        environment['CXX'] = compiler
    if paths.get('vulkan_icd'):
        if not Path(paths['vulkan_icd']).is_file():
            raise SystemExit('Configured Vulkan ICD is missing.')
        environment['VK_ICD_FILENAMES'] = paths['vulkan_icd']
    os.chdir(paths['protomotions_root'])
    os.execve(str(python), [str(python), '-I', '-B', str(script)]+sys.argv[2:], environment)


if __name__ == '__main__':
    main()
