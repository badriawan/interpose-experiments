"""CPU checks for runtime selection, credential removal and converter path scope."""
import ast
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'trial_01'))
from launcher import settings


def load(name):
    spec=importlib.util.spec_from_file_location('test_'+name,str(ROOT/'runtime'/(name+'.py')))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeWiringTests(unittest.TestCase):
    def test_converter_changes_only_temporary_constant(self):
        with mock.patch.object(settings,'load_config',return_value={'paths':{'protomotions_root':'/fixture'}}), mock.patch.object(settings,'verify_runtime_manifest'):
            module=load('sim_convert_bootstrap')
        tree=ast.parse('TMP_SMPL_DIR = "/tmp/smpl"\nvalue = 2 * 3\n')
        transformed=module.private_temporary_directory(tree,Path('/private/xml'))
        namespace={}
        exec(compile(transformed,'fixture','exec'),namespace)
        self.assertEqual(namespace['TMP_SMPL_DIR'],'/private/xml')
        self.assertEqual(namespace['value'],6)
        for source in ('TMP_SMPL_DIR = "/changed"','value = 3','TMP_SMPL_DIR = "/tmp/smpl"\nTMP_SMPL_DIR = "/tmp/smpl"'):
            with self.assertRaises(RuntimeError):module.private_temporary_directory(ast.parse(source),Path('/private'))

    def test_selected_python_environment_and_scrubbed_credentials(self):
        module=load('simulator_process')
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            config={'paths':{'simulator_python':str(base/'sim/bin/python'),'protomotions_root':str(base/'source')}}
            with mock.patch.object(settings,'ROOT',base), mock.patch.object(settings,'load_config',return_value=config), mock.patch.object(settings,'verify_runtime_manifest'), mock.patch.object(settings,'config_path',return_value=base/'runtime.json'), mock.patch.object(module.os,'chdir') as chdir, mock.patch.object(module.os,'execve') as execute, mock.patch.object(sys,'argv',['process',str(ROOT/'runtime/sim_eval_bootstrap.py'),'+headless=True']), mock.patch.dict(os.environ,{'OPENAI_API_KEY':'sentinel-not-a-real-key','ANTHROPIC_API_KEY':'sentinel'},clear=True):
                module.main()
            python,argv,environment=execute.call_args.args
            self.assertEqual(python,config['paths']['simulator_python'])
            self.assertEqual(argv[1:3],['-I','-B'])
            self.assertNotIn('OPENAI_API_KEY',environment)
            self.assertNotIn('ANTHROPIC_API_KEY',environment)
            self.assertEqual(environment['TORCH_EXTENSIONS_DIR'],str(base/'.local/cache/torch_extensions'))
            self.assertEqual(environment['TMPDIR'],str(base/'.local/tmp'))
            chdir.assert_called_once_with(config['paths']['protomotions_root'])

    def test_foreign_bootstrap_refused(self):
        module=load('simulator_process')
        with mock.patch.object(settings,'load_config',return_value={'paths':{}}), mock.patch.object(settings,'verify_runtime_manifest'), mock.patch.object(sys,'argv',['process','/foreign.py']), mock.patch.object(module.os,'execve') as execute:
            with self.assertRaises(SystemExit):module.main()
            execute.assert_not_called()

    def test_bridge_finite_headless_arguments(self):
        with mock.patch.object(settings,'load_config',return_value={'paths':{'protomotions_root':'/fixture'}}):
            bridge=load('stage10_simulator_bridge')
        args=bridge.evaluation_arguments('model','hands','motion','controls','output')
        for argument in ('+headless=True','+eval_overrides.num_envs=1','+agent.config.eval_num_episodes=1','+agent.config.eval_length=null'):
            self.assertIn(argument,args)
        with self.assertRaises(ValueError):bridge.evaluation_arguments('m','foreign','i','c','o')


if __name__=='__main__':unittest.main()
