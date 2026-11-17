"""Standard-library integration tests of saved synthetic evidence, not optimization."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from paper_replay.imported import import_metrics
from paper_replay.core import verify, Invalid

SAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'cma_method'

class CmaImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def snapshot(self, run='run-first', name='snapshot.json'):
        out = self.root / name
        result = subprocess.run([sys.executable, str(SAMPLE/'make_snapshot.py'),
                                 str(SAMPLE/run), '--out', str(out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return out

    def test_import_snapshot_and_execution_boundary(self):
        source = self.snapshot()
        data = json.loads(source.read_bytes())
        self.assertEqual(data['accounting']['experiment_plus_one_verification'], 5592)
        bundle = self.root/'receipt'
        receipt = import_metrics(SAMPLE/'import-contract.json', source, bundle, select='/metrics')
        self.assertEqual(receipt['status'], 'supported')
        self.assertIs(receipt['executed'], False)
        self.assertEqual(receipt['evidence_mode'], 'imported')
        self.assertEqual((bundle/'source-metrics.json').read_bytes(), source.read_bytes())
        self.assertEqual(verify(bundle)['integrity'], 'consistent')
        self.assertIn('does not authenticate execution', receipt['claims'][0]['statement'])

    def test_saved_repeat_snapshot_equal(self):
        self.assertEqual(self.snapshot().read_bytes(), self.snapshot('run-repeat','repeat.json').read_bytes())

    def test_trace_bytes_are_bound(self):
        source=self.snapshot(); bundle=self.root/'receipt'
        import_metrics(SAMPLE/'import-contract.json',source,bundle,select='/metrics')
        p=bundle/'source-metrics.json'; d=json.loads(p.read_bytes())
        d['run_evidence']['runs'][0]['seed']=999
        p.write_text(json.dumps(d),encoding='utf-8')
        with self.assertRaisesRegex(Invalid, 'artifact digest mismatch'):
            verify(bundle)

    def test_sample_checker_rejects_invalid_saved_result(self):
        run=self.root/'bad';shutil.copytree(SAMPLE/'run-first',run)
        p=run/'runs.json';d=json.loads(p.read_bytes());d['runs'][0]['best_point']=[3]*5
        p.write_text(json.dumps(d),encoding='utf-8');out=self.root/'invalid.json'
        result=subprocess.run([sys.executable,str(SAMPLE/'make_snapshot.py'),str(run),'--out',str(out)],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists())

    def test_snapshot_refuses_overwrite(self):
        out=self.snapshot();before=out.read_bytes()
        result=subprocess.run([sys.executable,str(SAMPLE/'make_snapshot.py'),str(SAMPLE/'run-first'),'--out',str(out)],capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertEqual(out.read_bytes(),before)
