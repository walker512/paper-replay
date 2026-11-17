import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from paper_replay.core import Invalid, evaluate, load_manifest, run, verify, write_json

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples/finite_difference'

class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'
        shutil.copytree(EXAMPLE, self.project)
        self.manifest = self.project / 'manifest.json'
        self.out = self.root / 'result'
    def tearDown(self): self.temp.cleanup()
    def alter(self, fn):
        m = json.loads(self.manifest.read_text()); fn(m)
        self.manifest.write_text(json.dumps(m))
    def script(self, source):
        p = self.project / 'experiment.py'; p.write_text(source)
        self.alter(lambda m: m['inputs'].update({'experiment.py': hashlib.sha256(p.read_bytes()).hexdigest()}))
    def execute(self): return run(self.manifest, self.out, execute=True)
    def test_metadata_bytes_utf8_lf_and_stable_order(self):
        a=self.root/'a.json'; b=self.root/'b.json'
        write_json(a,{'z':'中文','a':1})
        write_json(b,{'a':1,'z':'中文'})
        self.assertEqual(a.read_bytes(),b.read_bytes())
        self.assertNotIn(b'\r\n',a.read_bytes())
        self.assertEqual(json.loads(a.read_bytes()),{'z':'中文','a':1})
    def test_generated_manifest_is_utf8_lf(self):
        result=self.execute()
        data=(self.out/'manifest.json').read_bytes()
        self.assertNotIn(b'\r\n',data)
        self.assertEqual(hashlib.sha256(data).hexdigest(),result['manifest_sha256'])
        self.assertNotIn(b'\r\n',(self.out/'receipt.json').read_bytes())
        self.assertNotIn(b'\r\n',(self.out/'report.md').read_bytes())
    def test_legacy_windows_receipt_and_raw_tamper_detection(self):
        self.execute()
        mp=self.out/'manifest.json'; rp=self.out/'receipt.json'
        # Emulate a legitimate 0.1.0 Windows bundle exactly as emitted there.
        mp.write_bytes(mp.read_bytes().replace(b'\n',b'\r\n'))
        r=json.loads(rp.read_bytes());r['tool_version']='0.1.0'
        r['manifest_sha256']=hashlib.sha256(mp.read_bytes()).hexdigest()
        write_json(rp,r)
        self.assertEqual(verify(self.out)['integrity'],'consistent')
        # Transport conversion must not silently bypass byte-integrity checks.
        mp.write_bytes(mp.read_bytes().replace(b'\r\n',b'\n'))
        with self.assertRaises(Invalid): verify(self.out)
    def test_happy_and_verify(self):
        self.assertEqual(self.execute()['status'], 'supported')
        self.assertEqual(verify(self.out)['integrity'], 'consistent')
    def test_execution_opt_in(self):
        with self.assertRaises(Invalid): run(self.manifest, self.out)
        self.assertFalse(self.out.exists())
    def test_stale_directory(self):
        self.out.mkdir()
        with self.assertRaises(Invalid): self.execute()
    def test_input_tamper(self):
        (self.project / 'experiment.py').write_text('raise RuntimeError()')
        self.assertEqual(self.execute()['status'], 'input_mismatch')
        self.assertFalse((self.out / 'stdout.log').exists())
    def test_negative_claim(self):
        self.alter(lambda m: m['claims'][0].update(expected=3))
        self.assertEqual(self.execute()['status'], 'not_supported')
        verify(self.out)
    def test_missing_metric(self):
        self.alter(lambda m: m['claims'][0].update(metric='absent'))
        self.assertEqual(self.execute()['status'], 'insufficient_evidence')
    def test_nonzero_exit_never_passes(self):
        self.script('import sys,json\njson.dump({"estimated_order":2,"error_ratio":4},open(sys.argv[1],"w"))\nsys.exit(1)\n')
        self.assertEqual(self.execute()['status'], 'execution_error')
    def test_timeout(self):
        self.script('import time\ntime.sleep(1)')
        self.alter(lambda m:m.update(timeout_seconds=.02))
        self.assertEqual(self.execute()['status'], 'execution_error')
    def test_no_output(self):
        self.script('pass')
        self.assertEqual(self.execute()['status'], 'execution_error')
    def test_malformed_metrics(self):
        self.script('import sys\nopen(sys.argv[1],"w").write("{bad")')
        self.assertEqual(self.execute()['status'], 'execution_error')
    def test_duplicate_metrics(self):
        self.script('import sys\nopen(sys.argv[1],"w").write(\'{"estimated_order":2,"estimated_order":3}\')')
        self.assertEqual(self.execute()['status'], 'execution_error')
    def test_nan_metrics(self):
        self.script('import sys\nopen(sys.argv[1],"w").write(\'{"estimated_order":NaN}\')')
        self.assertEqual(self.execute()['status'], 'execution_error')
    def test_tampered_metrics_bundle(self):
        self.execute(); (self.out / 'metrics.json').write_text('{}')
        with self.assertRaises(Invalid): verify(self.out)
    def test_tampered_claim_receipt(self):
        self.execute(); p=self.out/'receipt.json'; r=json.loads(p.read_text())
        r['claims'][0]['observed']=123; p.write_text(json.dumps(r))
        with self.assertRaises(Invalid): verify(self.out)
    def test_escaping_input(self):
        self.alter(lambda m:m['inputs'].update({'../secret':'0'*64}))
        with self.assertRaises(Invalid): self.execute()
    def test_symlink_input_escape(self):
        outside=self.root/'outside.py';outside.write_text('pass')
        (self.project/'experiment.py').unlink(); (self.project/'experiment.py').symlink_to(outside)
        with self.assertRaises(Invalid): self.execute()
    def test_unpinned_script(self):
        self.alter(lambda m:m.update(command=['{python}','other.py','{output}']))
        with self.assertRaises(Invalid): self.execute()
    def test_negative_tolerance(self):
        self.alter(lambda m:m['claims'][0].update(absolute_tolerance=-1))
        with self.assertRaises(Invalid): load_manifest(self.manifest)
    def test_boolean_not_numeric(self):
        claims=load_manifest(self.manifest)['claims']
        self.assertEqual(evaluate(claims,{'estimated_order':True})[0]['status'],'insufficient_evidence')
    def test_duplicate_claim_ids(self):
        self.alter(lambda m:m['claims'].append(m['claims'][0]))
        with self.assertRaises(Invalid): load_manifest(self.manifest)
    def test_python_flag_entrypoint(self):
        (self.project/'-c').write_text('pass')
        self.alter(lambda m:m.update(inputs={'-c':hashlib.sha256(b'pass').hexdigest()},
                    command=['{python}','-c','print(123)','{output}']))
        with self.assertRaises(Invalid): self.execute()
    def test_receipt_metadata_tamper(self):
        self.execute(); p=self.out/'receipt.json'; r=json.loads(p.read_text())
        r['title']='different claim'; p.write_text(json.dumps(r))
        with self.assertRaises(Invalid): verify(self.out)
    def test_extreme_expected(self):
        self.alter(lambda m:m['claims'][0].update(expected=10**1000))
        with self.assertRaises(Invalid): load_manifest(self.manifest)
    def test_error_overflow(self):
        c={'id':'large','metric':'x','expected':1e308,'absolute_tolerance':0}
        r=evaluate([c],{'x':-1e308})[0]
        self.assertEqual(r['status'],'not_supported')
        self.assertIsNone(r['absolute_error'])
    def test_legacy_claim_numeric_bool_tamper_rejected(self):
        self.execute(); p=self.out/'receipt.json';r=json.loads(p.read_text())
        r['exit_code']=False;write_json(p,r)
        with self.assertRaises(Invalid): verify(self.out)
    def test_integer_difference_overflow(self):
        c={'id':'large','metric':'x','expected':-(10**308),'absolute_tolerance':0}
        r=evaluate([c],{'x':10**308})[0]
        self.assertEqual(r['status'],'not_supported')
        self.assertIsNone(r['absolute_error'])
    def test_input_modified_during_run(self):
        self.script('open("experiment.py","a").write("# changed")')
        self.assertEqual(self.execute()['status'],'input_mismatch')

if __name__ == '__main__': unittest.main()
