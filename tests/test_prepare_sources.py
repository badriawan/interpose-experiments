"""Local Git fixtures only: pinned sources, refusal guards and idempotent patches."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('prepare_sources_tested', str(ROOT/'scripts/prepare_sources.py'))
PREPARE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PREPARE
SPEC.loader.exec_module(PREPARE)


def run_git(folder, *args):
    environment = dict(os.environ)
    environment.update(GIT_AUTHOR_NAME='Fixture Author', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                       GIT_COMMITTER_NAME='Fixture Author', GIT_COMMITTER_EMAIL='fixture@example.invalid')
    result = subprocess.run(['git']+list(args), cwd=str(folder), env=environment,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class PrepareSourceTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'.local/testtmp').mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=str(ROOT/'.local/testtmp'))
        self.base = Path(self.temporary.name)
        self.origin = self.base/'origin';self.origin.mkdir()
        run_git(self.origin, 'init', '--quiet')
        (self.origin/'code.txt').write_text('original\n')
        run_git(self.origin, 'add', 'code.txt');run_git(self.origin, 'commit', '-qm', 'fixture')
        self.commit = run_git(self.origin, 'rev-parse', 'HEAD')
        self.source = PREPARE.Source('fixture', str(self.origin), self.commit)
        (self.origin/'code.txt').write_text('patched\n')
        patch_text = run_git(self.origin, 'diff')+'\n'
        self.patch = self.base/'fixture.patch';self.patch.write_text(patch_text)
        # Preserve the original fixture commit as the remote source.
        (self.origin/'code.txt').write_text('original\n')
        self.destination = self.base/'external/fixture'

    def tearDown(self):
        self.temporary.cleanup()

    def test_default_is_list_only_without_git_or_network(self):
        with mock.patch.object(PREPARE,'git',side_effect=AssertionError('Git attempted')), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(PREPARE.main([]),0)
        self.assertIn('list_only_no_network', output.getvalue())
        self.assertIn('5ee373310a75fa15719959b2808f8d399f27ae16',output.getvalue())

    def test_new_pinned_detached_checkout_and_patch_idempotence(self):
        result=PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual(result['status'],'new_checkout');self.assertEqual(result['patch'],'applied')
        self.assertEqual(run_git(self.destination,'rev-parse','HEAD'),self.commit)
        self.assertEqual((self.destination/'code.txt').read_text(),'patched\n')
        state_before=run_git(self.destination,'status','--porcelain')
        second=PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual(second['patch'],'already_applied')
        self.assertEqual(run_git(self.destination,'status','--porcelain'),state_before)

    def addition_patch(self):
        path = self.origin/'added.py'; path.write_text('trusted addition\n')
        run_git(self.origin, 'add', '-N', 'added.py')
        self.patch.write_text(run_git(self.origin, 'diff')+'\n')
        run_git(self.origin, 'reset', '--', 'added.py');path.unlink()

    def test_added_file_patch_is_idempotent_without_staging(self):
        self.addition_patch()
        first = PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual(first['patch'],'applied')
        self.assertEqual((self.destination/'added.py').read_text(),'trusted addition\n')
        second = PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual(second['patch'],'already_applied')
        self.assertEqual(run_git(self.destination,'diff','--cached','--name-only'),'')
        self.assertEqual(run_git(self.destination,'ls-files','--others','--exclude-standard'),'added.py')

    def test_added_file_tampering_is_rejected_and_preserved(self):
        self.addition_patch()
        PREPARE.prepare_source(self.source,self.destination,self.patch)
        (self.destination/'added.py').write_text('user changed addition\n')
        with self.assertRaises(PREPARE.PreparationError):
            PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual((self.destination/'added.py').read_text(),'user changed addition\n')

    def test_extra_untracked_after_added_patch_is_rejected(self):
        self.addition_patch()
        PREPARE.prepare_source(self.source,self.destination,self.patch)
        (self.destination/'unrelated.txt').write_text('user file\n')
        with self.assertRaisesRegex(PREPARE.PreparationError,'untracked'):
            PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual((self.destination/'unrelated.txt').read_text(),'user file\n')

    def test_existing_wrong_pin_is_preserved(self):
        PREPARE.prepare_source(self.source,self.destination)
        alternate=PREPARE.Source('fixture',str(self.origin),'0'*40)
        with self.assertRaisesRegex(PREPARE.PreparationError,'different commit'):
            PREPARE.prepare_source(alternate,self.destination)
        self.assertEqual(run_git(self.destination,'rev-parse','HEAD'),self.commit)

    def test_existing_untracked_and_staged_changes_refused(self):
        PREPARE.prepare_source(self.source,self.destination)
        extra=self.destination/'keep.txt';extra.write_text('keep me\n')
        with self.assertRaisesRegex(PREPARE.PreparationError,'untracked'):
            PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual(extra.read_text(),'keep me\n');extra.unlink()
        (self.destination/'code.txt').write_text('my edit\n');run_git(self.destination,'add','code.txt')
        with self.assertRaisesRegex(PREPARE.PreparationError,'staged'):
            PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual((self.destination/'code.txt').read_text(),'my edit\n')

    def test_unrelated_changes_after_patch_refused(self):
        PREPARE.prepare_source(self.source,self.destination,self.patch)
        (self.destination/'code.txt').write_text('patched\nextra edit\n')
        with self.assertRaisesRegex(PREPARE.PreparationError,'unrelated/partial'):
            PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual((self.destination/'code.txt').read_text(),'patched\nextra edit\n')

    def test_existing_regular_directory_refused(self):
        self.destination.mkdir(parents=True)
        (self.destination/'user.txt').write_text('preserve')
        with self.assertRaises(PREPARE.PreparationError):
            PREPARE.prepare_source(self.source,self.destination,self.patch)
        self.assertEqual((self.destination/'user.txt').read_text(),'preserve')

    def test_existing_branch_is_preserved(self):
        PREPARE.prepare_source(self.source,self.destination)
        run_git(self.destination,'checkout','-qb','user-branch')
        with self.assertRaisesRegex(PREPARE.PreparationError,'not detached'):
            PREPARE.prepare_source(self.source,self.destination)
        self.assertEqual(run_git(self.destination,'symbolic-ref','--short','HEAD'),'user-branch')

    def test_wrong_origin_refused(self):
        PREPARE.prepare_source(self.source,self.destination)
        run_git(self.destination,'remote','set-url','origin',str(self.base/'another'))
        with self.assertRaisesRegex(PREPARE.PreparationError,'origin differs'):
            PREPARE.prepare_source(self.source,self.destination)


if __name__ == '__main__':
    unittest.main()
