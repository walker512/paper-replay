import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from paper_replay.core import Invalid, read_json, write_json, verify
from paper_replay.imported import import_metrics, select_object

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.contract=self.root/'contract.json'; self.source=self.root/'metrics.json'
        self.out=self.root/'out'
        self.spec={'schema_version':1,'kind':'metric-contract','title':'Existing result',
                   'source':'Provided metrics; no origin or freshness assurance',
                   'claims':[{'id':'c1','statement':'x is approximately two','metric':'x',
                              'expected':2,'absolute_tolerance':0.1}]}
        write_json(self.contract,self.spec);write_json(self.source,{'x':2})
    def tearDown(self): self.temp.cleanup()
    def perform(self,select=''):
        return import_metrics(self.contract,self.source,self.out,select=select)
    def edit_receipt(self,fn):
        p=self.out/'receipt.json';r=read_json(p);fn(r);write_json(p,r)
    def test_readonly_no_execution(self):
        before=(self.source.read_bytes(),self.contract.read_bytes())
        with patch('subprocess.run',side_effect=AssertionError('must not run')):
            r=self.perform();v=verify(self.out)
        self.assertEqual(r['status'],'supported');self.assertFalse(v['executed'])
        self.assertEqual(v['evidence_mode'],'imported')
        self.assertEqual(before,(self.source.read_bytes(),self.contract.read_bytes()))
        self.assertIn('NOT a rerun',(self.out/'report.md').read_text())
    def test_negative_numeric(self):
        write_json(self.source,{'x':3})
        self.assertEqual(self.perform()['status'],'not_supported');verify(self.out)
    def test_missing_metric(self):
        write_json(self.source,{'other':2})
        self.assertEqual(self.perform()['status'],'insufficient_evidence');verify(self.out)
    def test_null_not_zero(self):
        write_json(self.source,{'x':None})
        self.assertEqual(self.perform()['status'],'insufficient_evidence')
    def test_dvc_json_export_explicit_pointer(self):
        write_json(self.source,{'':{'data':{'metrics.json':{'data':{'x':2}}}}})
        self.assertEqual(self.perform('//data/metrics.json/data')['status'],'supported');verify(self.out)
    def test_escaped_pointer(self):
        self.assertEqual(select_object({'a/b':{'~c':{'x':2}}},'/a~1b/~0c'),{'x':2})
    def test_array_selection_rejected(self):
        with self.assertRaises(Invalid):select_object({'x':[{'x':2}]},'/x/0')
    def test_bad_pointer_no_output(self):
        with self.assertRaises(Invalid):self.perform('/absent')
        self.assertFalse(self.out.exists())
    def test_bad_escape(self):
        with self.assertRaises(Invalid):self.perform('/~2')
    def test_duplicate_source_keys(self):
        self.source.write_bytes(b'{"x":2,"x":3}')
        with self.assertRaises(Invalid):self.perform()
    def test_oversized_source(self):
        self.source.write_bytes(b' '*2_000_001)
        with self.assertRaises(Invalid):self.perform()
    def test_nan_source(self):
        self.source.write_bytes(b'{"x":NaN}')
        with self.assertRaises(Invalid):self.perform()
    def test_decimal_overflow_rejected_before_output(self):
        self.source.write_bytes(b'{"x":1e309}')
        with self.assertRaises(Invalid):self.perform()
        self.assertFalse(self.out.exists())
    def test_deep_json_no_partial_output(self):
        self.source.write_bytes(b'{"x":2,"deep":'+b'['*1100+b'0'+b']'*1100+b'}')
        with self.assertRaises(Invalid):self.perform()
        self.assertFalse(self.out.exists())
    def test_depth_limit_even_below_python_recursion_limit(self):
        self.source.write_bytes(b'{"x":2,"deep":'+b'['*70+b'0'+b']'*70+b'}')
        with self.assertRaises(Invalid):self.perform()
        self.assertFalse(self.out.exists())
    def test_surrogate_no_partial_output(self):
        self.source.write_bytes(b'{"x":2,"note":"\\ud800"}')
        with self.assertRaises(Invalid):self.perform()
        self.assertFalse(self.out.exists())
    def test_booleans_cannot_replace_numeric_claim_fields(self):
        self.spec['claims'][0]['expected']=1
        write_json(self.contract,self.spec);write_json(self.source,{'x':1})
        self.perform(); original=read_json(self.out/'receipt.json')
        for key,value in [('observed',True),('expected',True),('absolute_error',False)]:
            with self.subTest(field=key):
                r=json.loads(json.dumps(original));r['claims'][0][key]=value
                write_json(self.out/'receipt.json',r)
                with self.assertRaises(Invalid):verify(self.out)
    @unittest.skipUnless(hasattr(os,'mkfifo'),'FIFO regression requires POSIX')
    def test_fifo_verification_returns_without_blocking(self):
        self.perform(); p=self.out/'contract.json';p.unlink();os.mkfifo(p)
        probe="from pathlib import Path; from paper_replay.core import verify,Invalid; import sys\ntry: verify(Path(sys.argv[1]))\nexcept Invalid: sys.exit(0)\nelse: sys.exit(3)"
        result=subprocess.run([sys.executable,'-c',probe,str(self.out)],capture_output=True,timeout=2)
        self.assertEqual(result.returncode,0,result.stderr)
    @unittest.skipUnless(hasattr(os,'mkfifo'),'FIFO regression requires POSIX')
    def test_fifo_artifact_digest_returns_without_blocking(self):
        self.perform(); p=self.out/'source-metrics.json';p.unlink();os.mkfifo(p)
        probe="from pathlib import Path; from paper_replay.core import verify,Invalid; import sys\ntry: verify(Path(sys.argv[1]))\nexcept Invalid: sys.exit(0)\nelse: sys.exit(3)"
        result=subprocess.run([sys.executable,'-c',probe,str(self.out)],capture_output=True,timeout=2)
        self.assertEqual(result.returncode,0,result.stderr)
    def test_serialized_output_size_preflight_no_partial(self):
        # Compact JSON fits input limit; pretty-printing its array would exceed it.
        self.source.write_bytes(b'{"x":2,"unused":['+b'0,'*300000+b'0]}')
        with self.assertRaises(Invalid):self.perform()
        self.assertFalse(self.out.exists())
    def test_execution_fields_contract_rejected(self):
        self.spec['command']=['python','untrusted.py'];write_json(self.contract,self.spec)
        with self.assertRaises(Invalid):self.perform()
    def test_reject_receipt_execution_claim(self):
        self.perform();self.edit_receipt(lambda r:r.update(executed=True))
        with self.assertRaises(Invalid):verify(self.out)
    def test_reject_exit_code_field(self):
        self.perform();self.edit_receipt(lambda r:r.update(exit_code=0))
        with self.assertRaises(Invalid):verify(self.out)
    def test_reject_source_tamper(self):
        self.perform();(self.out/'source-metrics.json').write_bytes(b'{"x":3}')
        with self.assertRaises(Invalid):verify(self.out)
    def test_rehashed_transformation_tamper(self):
        self.perform();p=self.out/'metrics.json';write_json(p,{'x':3})
        self.edit_receipt(lambda r:r['artifacts'].update({'metrics.json':hashlib.sha256(p.read_bytes()).hexdigest()}))
        with self.assertRaises(Invalid):verify(self.out)
    def test_source_snapshot_survives_source_changes(self):
        self.perform();self.source.write_bytes(b'{"x":3}')
        self.assertEqual(verify(self.out)['status'],'supported')
    def test_existing_directory(self):
        self.out.mkdir()
        with self.assertRaises(Invalid):self.perform()
    def test_contract_metadata_tamper(self):
        self.perform();self.edit_receipt(lambda r:r.update(source='False source'))
        with self.assertRaises(Invalid):verify(self.out)

if __name__=='__main__':unittest.main()
