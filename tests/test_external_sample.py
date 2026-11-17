"""Actual upstream aggregation; separate from our synthetic mechanism tests."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from paper_replay.core import run, verify

SOURCE = Path(__file__).resolve().parents[1] / 'examples/speceval_table1'

class ExternalSampleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        shutil.copytree(SOURCE, self.project)
        self.manifest = self.project / 'manifest.json'
    def tearDown(self): self.temp.cleanup()
    def test_all_sixteen_paper_cells(self):
        result=run(self.manifest,self.root/'out',execute=True)
        self.assertEqual(result['status'],'supported')
        self.assertEqual(len(result['claims']),16)
        self.assertAlmostEqual(result['claims'][3]['observed'],87.24758406997086)
        self.assertEqual(verify(self.root/'out')['status'],'supported')
    def test_changed_released_data_is_not_silent(self):
        p=self.project/'upstream/results/replay/hbn_pair_results.csv'
        p.write_bytes(p.read_bytes()+b'\n')
        result=run(self.manifest,self.root/'out',execute=True)
        self.assertEqual(result['status'],'input_mismatch')
    def test_original_upstream_rejects_missing_grid_even_if_rehashed(self):
        name='upstream/results/replay/hbn_pair_results.csv'
        p=self.project/name
        p.write_bytes(b'\n'.join(p.read_bytes().splitlines()[:-1])+b'\n')
        m=json.loads(self.manifest.read_text())
        m['inputs'][name]=hashlib.sha256(p.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps(m))
        result=run(self.manifest,self.root/'out',execute=True)
        self.assertEqual(result['status'],'execution_error')
        self.assertEqual(result['claims'],[])

if __name__=='__main__': unittest.main()
