"""Saved-result preview validation; optional media smoke uses a tiny own fixture."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('render_trial_result',str(ROOT/'scripts/render_trial_result.py'))
preview=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preview)
MEDIA_AVAILABLE=all(importlib.util.find_spec(name) is not None for name in ('matplotlib','imageio','imageio_ffmpeg'))


def fixture():
    joints=np.zeros((1,4,24,3),dtype=np.float64)
    joints[0,:,:,2]=np.linspace(.1,1.7,24)
    centers=np.zeros((1,4,3));centers[:,:,0]=.4;centers[:,:,2]=[.5,.65,.65,.5]
    return {'human':{'joint_xyz':joints},'object':{'floorlamp':{'xyz':centers}},
            'metadata':{'fps':30,'position_joint_parent_indices':[-1]+[0]*23}}


class SavedResultTests(unittest.TestCase):
    def test_validated_positions_are_independent_copies(self):
        data=fixture();original=data['human']['joint_xyz'].copy()
        value=preview.validate_motion(data)
        self.assertEqual(value['joints'].shape,(4,24,3))
        self.assertEqual(value['centers'].shape,(4,3))
        value['joints'][0,0,0]=10
        np.testing.assert_array_equal(data['human']['joint_xyz'],original)

    def test_invalid_parent_graphs_and_nonintegers(self):
        for parents in ([-1]+[24]*23,[-1,2,1]+[0]*21,[0]*24,[-1]+[0.0]*23,[-1]+[True]*23):
            data=fixture();data['metadata']['position_joint_parent_indices']=parents
            with self.assertRaises(ValueError):preview.validate_motion(data)

    def test_nonfinite_wrong_shape_and_multiple_objects(self):
        bad=[]
        data=fixture();data['human']['joint_xyz'][0,0,0,0]=np.nan;bad.append(data)
        data=fixture();data['object']['floorlamp']['xyz'][0,0,0]=np.inf;bad.append(data)
        data=fixture();data['object']['floorlamp']['xyz']=np.zeros((1,3,3));bad.append(data)
        data=fixture();data['human']['joint_xyz']=np.zeros((2,4,24,3));bad.append(data)
        data=fixture();data['object']['other']=copy.deepcopy(data['object']['floorlamp']);bad.append(data)
        for data in bad:
            with self.assertRaises(ValueError):preview.validate_motion(data)
        for fps in (0,-1,np.nan,np.inf,True,'30'):
            data=fixture();data['metadata']['fps']=fps
            with self.assertRaises(ValueError):preview.validate_motion(data)

    def test_pickle_acknowledgement_is_required_before_load(self):
        with mock.patch.object(preview.np,'load') as loader:
            with self.assertRaises(ValueError):preview.load_motion(Path('untrusted.npy'))
            loader.assert_not_called()

    def test_each_existing_preview_file_is_preserved(self):
        for name in preview.NAMES:
            with tempfile.TemporaryDirectory() as temporary:
                output=Path(temporary);existing=output/name;existing.write_bytes(b'preserve-me')
                with self.assertRaises(ValueError):preview.render(output/'absent.npy',output,True)
                self.assertEqual(existing.read_bytes(),b'preserve-me')
                self.assertEqual(len(list(output.iterdir())),1)

    @unittest.skipUnless(MEDIA_AVAILABLE,'Optional media packages not installed.')
    def test_small_video_decodes_and_source_is_unchanged(self):
        import imageio.v2 as imageio
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary);source=folder/'own_fixture.npy';output=folder/'preview'
            np.save(str(source),fixture());before=source.read_bytes()
            report=preview.render(source,output,True)
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(report['frames'],4)
            self.assertEqual(report['fps'],30)
            self.assertEqual(report['source_file'],'own_fixture.npy')
            self.assertNotIn(str(folder),(output/preview.NAMES[2]).read_text())
            self.assertFalse(report['new_simulation_run'])
            self.assertFalse(report['physical_success_verified'])
            with imageio.get_reader(str(output/preview.NAMES[0])) as reader:
                # imageio's FFmpeg reader reports an infinite length; list()
                # uses that length hint and can request an enormous allocation.
                frames=[frame for frame in reader]
            self.assertEqual(len(frames),4)
            self.assertEqual(frames[0].shape,(700,1120,3))
            self.assertEqual(imageio.imread(str(output/preview.NAMES[1])).shape,(700,1120,3))
            self.assertEqual(json.loads((output/preview.NAMES[2]).read_text())['source_sha256'],preview.digest(source))


if __name__=='__main__':unittest.main()
