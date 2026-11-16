"""CPU regression tests for synthetic validation, relocation and integrity refusal."""
import builtins
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ROOT.joinpath('.local/testtmp').mkdir(parents=True, exist_ok=True)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    loaded = importlib.util.module_from_spec(spec); spec.loader.exec_module(loaded)
    return loaded


class PortableTrialTests(unittest.TestCase):
    def setUp(self):
        self.demo = module('demo', ROOT/'scripts/offline_demo.py')

    def test_valid_actual_validator_and_retimer(self):
        goal, plan = self.demo.fixture()
        result = self.demo.validate(plan, goal)
        self.assertEqual(result['status'], 'SYNTHETIC_VALIDATION_PASS')
        self.assertFalse(result['motion_generated'])
        self.assertGreater(result['number_frames'], 150)

    def test_invalid_duration(self):
        goal, plan = self.demo.fixture(); plan['object_points'][0][2][0] = 179
        with self.assertRaises(ValueError): self.demo.validate(plan, goal)
        goal['hold_duration_s'] = 0
        with self.assertRaises(ValueError): self.demo.validate(plan, goal)

    def test_nonincreasing_and_malformed(self):
        for mutate in (lambda p:p['object_points'][0][2].__setitem__(0,30),
                       lambda p:p.__setitem__('object_points', [[[0,1,2]]]),
                       lambda p:p.__setitem__('control_points', [])):
            goal, plan = self.demo.fixture(); mutate(plan)
            with self.assertRaises(ValueError): self.demo.validate(plan, goal)

    def test_offline_no_heavy_import_network_or_credential(self):
        original_import = builtins.__import__; original_open = builtins.open
        def guarded_import(name, *args, **kwargs):
            if name.split('.')[0] in ('torch','openai','isaacgym','pytorch3d','human_body_prior'):
                raise AssertionError('Heavy import attempted: '+name)
            return original_import(name, *args, **kwargs)
        def guarded_open(file, *args, **kwargs):
            if 'openai_api_key' in str(file) or 'runtime.json' in str(file):
                raise AssertionError('Private runtime/credential access attempted')
            return original_open(file, *args, **kwargs)
        with mock.patch('builtins.__import__', guarded_import), mock.patch('builtins.open', guarded_open), mock.patch('io.open', guarded_open), mock.patch.object(socket.socket,'connect', side_effect=AssertionError('Network attempted')), mock.patch.object(socket,'create_connection',side_effect=AssertionError('Network attempted')):
            goal, plan = self.demo.fixture(); self.demo.validate(plan, goal)

    def test_relocated_without_external_tree(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT/'.local/testtmp')) as temp:
            root = Path(temp)/'moved'; (root/'scripts').mkdir(parents=True)
            shutil.copytree(str(ROOT/'trial_01/executor_code'), str(root/'trial_01/executor_code'))
            shutil.copy2(str(ROOT/'scripts/offline_demo.py'), str(root/'scripts/offline_demo.py'))
            environment = dict(os.environ); environment.pop('PYTHONPATH',None)
            environment['INTERPOSE_LAB_CONFIG'] = str(root/'does-not-exist.json')
            result = subprocess.run([sys.executable,'-I','-B',str(root/'scripts/offline_demo.py')],cwd=str(root),env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE, text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((root/'.local/offline_demo.json').is_file())

    def test_hash_tamper_is_rejected(self):
        settings = module('settings_test', ROOT/'trial_01/launcher/settings.py')
        with tempfile.TemporaryDirectory(dir=str(ROOT/'.local/testtmp')) as temp:
            base = Path(temp); (base/'manifests').mkdir(); (base/'.local').mkdir()
            source = base/'external.py'; source.write_text('trusted source\n')
            package = base/'package.py'; package.write_text('trusted package\n')
            h = settings.digest
            entries = [{'root':'interpose_root','path':'external.py','sha256':h(source)}]
            (base/'manifests/dependency_files.json').write_text(json.dumps({'entries':entries}))
            (base/'manifests/package_files.json').write_text(json.dumps({'sha256':{'package.py':h(package)}}))
            paths = {key:str(base) for key in settings.REQUIRED}; paths['key_file']=str(base/'never-read-key')
            config={'schema_version':1,'paths':paths,'api':{'model':'gpt-4o'}}
            config_path=base/'.local/runtime.json';config_path.write_text(json.dumps(config))
            with mock.patch.object(settings,'ROOT',base),mock.patch.dict(os.environ,{'INTERPOSE_LAB_CONFIG':str(config_path)}):
                manifest=settings.verify_expected(settings.load_config())
                settings.manifest_path().write_text(json.dumps(manifest));settings.verify_runtime_manifest()
                source.write_text('tampered source\n')
                with self.assertRaisesRegex(ValueError,'hash mismatch'):settings.verify_runtime_manifest()
                source.write_text('trusted source\n');package.write_text('tampered package\n')
                with self.assertRaisesRegex(ValueError,'package hash mismatch'):settings.verify_runtime_manifest()


if __name__ == '__main__': unittest.main()
