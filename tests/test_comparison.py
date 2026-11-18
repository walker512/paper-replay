import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from paper_replay import core, comparison
from paper_replay.imported import import_metrics

ROOT=Path(__file__).resolve().parents[1]

class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.spec={'schema_version':1,'kind':'metric-contract','title':'Synthetic','source':'manual',
                   'claims':[{'id':'x','statement':'x near two','metric':'x','expected':2,'absolute_tolerance':0.1}]}
        self.a=self.imported('a',{'x':1});self.b=self.imported('b',{'x':2})
    def tearDown(self): self.tmp.cleanup()
    def imported(self,name,metrics,spec=None,select=''):
        contract=self.root/(name+'-contract.json'); data=self.root/(name+'-data.json')
        core.write_json(contract,spec or self.spec);core.write_json(data,metrics)
        out=self.root/name;import_metrics(contract,data,out,select=select);return out
    def report(self,a=None,b=None):
        return core.parse_json_bytes(comparison.analyze(comparison.capture(a or self.a),comparison.capture(b or self.b)))
    def test_status_transition_is_not_improvement(self):
        r=self.report();self.assertEqual(r['before']['status'],'not_supported');self.assertEqual(r['after']['status'],'supported')
        self.assertFalse(r['improvement_established']);self.assertEqual(r['before']['mode'],'imported')
        self.assertIsNone(r['before']['input_sha256_declarations'])
        self.assertEqual(r['metric_changes'][0]['before'],{'present':True,'value':1})
    def test_missing_null_bool_not_zero(self):
        b=self.imported('missing',{'y':None,'z':False})
        r=self.report(b=b);self.assertEqual(r['after']['status'],'insufficient_evidence')
        rows={x['key']:x for x in r['metric_changes']}
        self.assertEqual(rows['x']['after'],{'present':False,'value':None})
        self.assertEqual(rows['y']['after'],{'present':True,'value':None})
        self.assertEqual(rows['z']['after'],{'present':True,'value':False})
    def test_widened_removed_and_changed_claims(self):
        spec=copy.deepcopy(self.spec);spec['claims'].append(dict(spec['claims'][0],id='removed'))
        a=self.imported('old',{'x':1},spec)
        spec['claims']=spec['claims'][:1];spec['claims'][0]['absolute_tolerance']=2
        b=self.imported('wide',{'x':1},spec);r=self.report(a,b)
        rows={x['id']:x for x in r['claim_changes']}
        self.assertIn('tolerance_widened',rows['x']['flags']);self.assertIn('claim_removed',rows['removed']['flags'])
        self.assertFalse(r['improvement_established'])
    def test_selection_change_visible(self):
        a=self.imported('sel1',{'a':{'x':1},'b':{'x':2}},select='/a')
        b=self.imported('sel2',{'a':{'x':1},'b':{'x':2}},select='/b')
        r=self.report(a,b);self.assertEqual(r['before']['selection'],'/a');self.assertIn('Imported selection changed',str(r['warnings']))
    def executed(self,name,text='import json,sys;json.dump({"x":2},open(sys.argv[1],"w"))'):
        project=self.root/(name+'project');project.mkdir();script=project/'run.py';script.write_text(text)
        spec={'schema_version':1,'title':'Synthetic execution','source':'manual','claims':self.spec['claims'],
              'inputs':{'run.py':hashlib.sha256(script.read_bytes()).hexdigest()},'command':['{python}','run.py','{output}'],
              'metrics':'{output}','timeout_seconds':2}
        core.write_json(project/'manifest.json',spec);out=self.root/name
        core.run(project/'manifest.json',out,execute=True);return out
    def test_real_execution_input_changes_and_mixed_modes(self):
        a=self.executed('exec1');b=self.executed('exec2','import json,sys;json.dump({"x":3},open(sys.argv[1],"w"))')
        r=self.report(a,b);self.assertEqual(r['before']['mode'],'execution_receipt')
        self.assertNotEqual(r['before']['entry_script_sha256_declaration'],r['after']['entry_script_sha256_declaration'])
        self.assertIn('Declared inputs',str(r['warnings']))
        mixed=self.report(a,self.b);self.assertIn('Evidence mode changed',str(mixed['warnings']))
    def test_failed_execution_metrics_not_evaluated(self):
        a=self.executed('failed','import json,sys;json.dump({"x":999},open(sys.argv[1],"w"));sys.exit(1)')
        r=self.report(a,self.b);self.assertFalse(r['before']['metrics_evaluated'])
        self.assertEqual(r['metric_changes'][0]['before'],{'present':False,'value':None})
    def test_deterministic_build_and_offline_verify(self):
        outputs=[]
        for i in range(2):
            out=self.root/('out'+str(i));comparison.build(self.a,self.b,out);comparison.verify(out)
            outputs.append({str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()})
        self.assertEqual(outputs[0],outputs[1]);self.assertNotIn('before/report.md',outputs[0])
        # After original deletion, snapshot verification still works.
        import shutil
        shutil.rmtree(self.a);shutil.rmtree(self.b);comparison.verify(self.root/'out0')
    def test_all_snapshot_and_report_tampering_rejected(self):
        out=self.root/'out';comparison.build(self.a,self.b,out)
        for p in [p for p in out.rglob('*') if p.is_file()]:
            with self.subTest(path=p.name):
                old=p.read_bytes();p.write_bytes(old+b'X')
                with self.assertRaises((core.Invalid,ValueError)):comparison.verify(out)
                p.write_bytes(old)
        (out/'before'/'extra').write_text('x')
        with self.assertRaises(core.Invalid):comparison.verify(out)
    def test_corrupt_input_preflight_no_output(self):
        (self.a/'metrics.json').write_text('{"x":999}')
        out=self.root/'out'
        with self.assertRaises(core.Invalid):comparison.build(self.a,self.b,out)
        self.assertFalse(out.exists())
    def test_symlink_and_special_file_rejected(self):
        target=self.a/'metrics.json';raw=target.read_bytes();target.unlink()
        keep=self.root/'keep';keep.write_bytes(raw)
        try:target.symlink_to(keep)
        except (OSError,NotImplementedError):self.skipTest('symlinks unsupported')
        with self.assertRaises((core.Invalid,OSError)):comparison.capture(self.a)
        self.assertEqual(keep.read_bytes(),raw)
    @unittest.skipUnless(os.name=='posix','FIFO POSIX only')
    def test_fifo_nonblocking_rejected(self):
        p=self.a/'metrics.json';p.unlink();os.mkfifo(p)
        with self.assertRaises((core.Invalid,OSError)):comparison.capture(self.a)
    def test_exclusive_output_and_concurrent_creation(self):
        out=self.root/'out'
        def attempt(_):
            try:comparison.build(self.a,self.b,out);return True
            except FileExistsError:return False
        with ThreadPoolExecutor(max_workers=8) as pool:self.assertEqual(sum(pool.map(attempt,range(8))),1)
        before=(out/'comparison.json').read_bytes()
        with self.assertRaises(FileExistsError):comparison.build(self.a,self.b,out)
        self.assertEqual(before,(out/'comparison.json').read_bytes());comparison.verify(out)
    @unittest.skipUnless(os.name=='posix','POSIX bits not Windows ACL')
    def test_private_creation_umasks(self):
        for mask in (0,0o22):
            old=os.umask(mask)
            try:
                out=self.root/('mode'+str(mask));comparison.build(self.a,self.b,out)
            finally:os.umask(old)
            self.assertEqual(out.stat().st_mode & 0o777,0o700)
            for p in out.rglob('*'):self.assertEqual(p.stat().st_mode & 0o777,0o700 if p.is_dir() else 0o600)
    def test_partial_failure_no_completion_and_no_retry(self):
        out=self.root/'out';original=comparison.write_files
        def fail(root,data):
            if root==out/'after':raise OSError('injected')
            return original(root,data)
        with patch.object(comparison,'write_files',fail):
            with self.assertRaises(OSError):comparison.build(self.a,self.b,out)
        self.assertFalse((out/'comparison.json').exists())
        with self.assertRaises(core.Invalid):comparison.verify(out)
        with self.assertRaises(FileExistsError):comparison.build(self.a,self.b,out)
    def test_actual_cli_and_private_errors(self):
        out=self.root/'out'
        def cli(*args):return subprocess.run([sys.executable,'-m','paper_replay',*map(str,args)],cwd=ROOT,capture_output=True)
        r=cli('compare-runs',self.a,self.b,'--out',out);self.assertEqual(r.returncode,0,r.stderr)
        r=cli('compare-verify',out);self.assertEqual(r.returncode,0,r.stderr)
        (self.a/'receipt.json').write_text('{"artifacts":{"PRIVATE/escape":"x"}}')
        r=cli('compare-runs',self.a,self.b,'--out',self.root/'bad')
        self.assertEqual(r.returncode,1);self.assertNotIn(b'PRIVATE',r.stderr);self.assertNotIn(str(self.root).encode(),r.stderr);self.assertNotIn(b'Traceback',r.stderr)
    def test_capture_is_verified_not_live_inputs_reopened(self):
        data=comparison.capture(self.a)
        (self.a/'metrics.json').write_text('{"x":1234}')
        r=core.parse_json_bytes(comparison.analyze(data,comparison.capture(self.b)))
        self.assertEqual(r['metric_changes'][0]['before']['value'],1)

    def test_bounds_and_output_member_symlink(self):
        with patch.object(comparison,'LIMIT',1):
            with self.assertRaises(core.Invalid):comparison.capture(self.a)
        out=self.root/'out';keep=self.root/'keep';keep.write_bytes(b'KEEP')
        original=os.open;injected=[]
        def opened(path,flags,mode=0o777,**kw):
            if Path(path)==out/'comparison.json' and flags & os.O_CREAT:
                try:Path(path).symlink_to(keep)
                except (OSError,NotImplementedError):self.skipTest('symlinks unsupported')
                injected.append(True)
            return original(path,flags,mode,**kw)
        with patch.object(comparison.os,'open',opened):
            with self.assertRaises(FileExistsError):comparison.build(self.a,self.b,out)
        self.assertTrue(injected);self.assertEqual(keep.read_bytes(),b'KEEP')
        with self.assertRaises((core.Invalid,OSError)):comparison.verify(out)

    def test_malformed_receipt_cli_does_not_leak(self):
        for payload in ([], {'artifacts':[]}, {'artifacts':{'/PRIVATE':0}},
                        {'artifacts':{'metrics.json':None},'schema_version':2}):
            (self.a/'receipt.json').write_text(json.dumps(payload))
            r=subprocess.run([sys.executable,'-m','paper_replay','compare-runs',str(self.a),str(self.b),
                              '--out',str(self.root/'bad')],cwd=ROOT,capture_output=True)
            self.assertEqual(r.returncode,1);self.assertNotIn(b'PRIVATE',r.stderr)
            self.assertNotIn(b'Traceback',r.stderr);self.assertNotIn(str(self.root).encode(),r.stderr)
            self.assertFalse((self.root/'bad').exists())

if __name__=='__main__':unittest.main()
