"""Exercise actual receiver CLI exit codes, without trusting process-success as claim-success."""
import hashlib
import shutil
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from paper_replay.core import write_json, run
from paper_replay.imported import import_metrics

class ReceiverGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.contract=self.root/'contract.json';self.source=self.root/'source.json';self.bundle=self.root/'bundle'
        write_json(self.contract,{'schema_version':1,'kind':'metric-contract','title':'Receiver gate',
            'source':'Synthetic fixture, not authenticated science',
            'claims':[{'id':'c','statement':'x is one','metric':'x','expected':1,'absolute_tolerance':0}]})
    def make(self,metrics):
        write_json(self.source,metrics);import_metrics(self.contract,self.source,self.bundle)
    def cli(self,strict=False):
        return subprocess.run([sys.executable,'-m','paper_replay','verify',str(self.bundle)]+
            (['--require-supported'] if strict else []),capture_output=True,text=True)
    def test_supported_passes_both_and_preserves_import_label(self):
        self.make({'x':1})
        for strict in (False,True):
            result=self.cli(strict);self.assertEqual(result.returncode,0,result.stderr)
            self.assertIs(json.loads(result.stdout)['executed'],False)
    def test_negative_consistent_bundle_only_fails_explicit_gate(self):
        self.make({'x':2});self.assertEqual(self.cli().returncode,0)
        result=self.cli(True);self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['integrity'],'consistent')
        self.assertEqual(json.loads(result.stdout)['status'],'not_supported')
    def test_missing_claim_fails_gate(self):
        self.make({});self.assertEqual(self.cli().returncode,0)
        result=self.cli(True);self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['status'],'insufficient_evidence')
    def test_tampered_bundle_errors_in_both_modes(self):
        self.make({'x':1});(self.bundle/'metrics.json').write_text('{"x":9}')
        for strict in (False,True):self.assertEqual(self.cli(strict).returncode,1)
    def test_missing_bundle_errors_in_both_modes(self):
        for strict in (False,True):self.assertEqual(self.cli(strict).returncode,1)

    def execution_bundle(self, fail=False):
        example=Path(__file__).resolve().parents[1]/'examples'/'finite_difference'
        project=self.root/'project';shutil.copytree(example,project)
        manifest=project/'manifest.json'
        if fail:
            script=project/'experiment.py';script.write_bytes(b'raise SystemExit(3)\n')
            spec=json.loads(manifest.read_bytes())
            spec['inputs']['experiment.py']=hashlib.sha256(script.read_bytes()).hexdigest()
            write_json(manifest,spec)
        return run(manifest,self.bundle,execute=True)
    def test_execution_receipt_supported_passes_gate(self):
        self.execution_bundle();self.assertEqual(self.cli(True).returncode,0)
    def test_execution_failure_consistent_but_gate_fails(self):
        receipt=self.execution_bundle(fail=True)
        self.assertNotEqual(receipt['status'],'supported')
        self.assertEqual(self.cli().returncode,0)
        self.assertEqual(self.cli(True).returncode,2)

    def test_input_fingerprint_mismatch_consistent_but_gate_fails(self):
        example=Path(__file__).resolve().parents[1]/'examples'/'finite_difference'
        project=self.root/'changed-project';shutil.copytree(example,project)
        # Deliberately do not update the manifest pin; run must not execute this file.
        (project/'experiment.py').write_bytes(b'raise RuntimeError("must not execute")\n')
        receipt=run(project/'manifest.json',self.bundle,execute=True)
        self.assertEqual(receipt['status'],'input_mismatch')
        self.assertFalse((self.bundle/'metrics.json').exists())
        self.assertNotIn('exit_code',receipt)
        for strict,expected in ((False,0),(True,2)):
            result=self.cli(strict)
            self.assertEqual(result.returncode,expected,result.stderr)
            parsed=json.loads(result.stdout)
            self.assertEqual(parsed['integrity'],'consistent')
            self.assertEqual(parsed['status'],'input_mismatch')
