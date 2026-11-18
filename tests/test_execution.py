import hashlib,json,os,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from paper_replay import core
from paper_replay.execution import Cancelled,LOG_LIMIT,cancellation

class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.out=self.root/'result';self.manifest=self.root/'manifest.json'
    def script(self,source,timeout=2):
        p=self.root/'experiment.py';p.write_text(source)
        m={'schema_version':1,'title':'Synthetic lifecycle case','source':'original fixture','inputs':{'experiment.py':hashlib.sha256(p.read_bytes()).hexdigest()},'command':['{python}','experiment.py','{output}'],'timeout_seconds':timeout,'metrics':'{output}','claims':[{'id':'one','statement':'one','metric':'x','expected':1,'absolute_tolerance':0}]}
        self.manifest.write_text(json.dumps(m))
    def run_case(self):return core.run(self.manifest,self.out,execute=True)
    def test_stdout_limit(self):
        self.script("import os\nwhile True: os.write(1,b'x'*65536)")
        r=self.run_case();self.assertEqual(r['status'],'execution_error');self.assertIn('log limit',r['error']);self.assertEqual((self.out/'stdout.log').stat().st_size,LOG_LIMIT);self.assertEqual(core.verify(self.out)['status'],'execution_error')
    def test_stderr_limit(self):
        self.script("import os\nwhile True: os.write(2,b'x'*65536)")
        r=self.run_case();self.assertEqual(r['status'],'execution_error');self.assertEqual((self.out/'stderr.log').stat().st_size,LOG_LIMIT)
    def test_fast_exit_oversize_never_supported(self):
        self.script("import os,sys,json\nos.write(1,b'x'*2000000)\nopen(sys.argv[1],'w').write(json.dumps({'x':1}))")
        self.assertEqual(self.run_case()['status'],'execution_error')
    def test_success_preserves_logs_and_metrics(self):
        self.script("import sys,json\nprint('control')\nopen(sys.argv[1],'w').write(json.dumps({'x':1}))")
        self.assertEqual(self.run_case()['status'],'supported');self.assertEqual((self.out/'stdout.log').read_text(),'control\n');self.assertEqual(core.verify(self.out)['status'],'supported')
    def test_timeout(self):
        self.script('import time\ntime.sleep(10)',.1)
        r=self.run_case();self.assertEqual(r['status'],'execution_error');self.assertIn('timed out',r['error'])
    @unittest.skipUnless(os.name=='posix','POSIX process-group behavior only')
    def test_descendant_cleanup_after_parent_exit_and_timeout(self):
        for hanging in (False,True):
            self.out=self.root/('out'+str(hanging));marker=self.root/('marker'+str(hanging))
            child="import time,pathlib;time.sleep(.6);pathlib.Path(%r).write_text('escaped')"%str(marker)
            self.script("import subprocess,sys,time,json\nsubprocess.Popen([sys.executable,'-c',%r])\nopen(sys.argv[1],'w').write(json.dumps({'x':1}))\n"%child+('time.sleep(10)' if hanging else ''),.2)
            r=self.run_case();self.assertEqual(r['status'],'execution_error' if hanging else 'supported');time.sleep(.75);self.assertFalse(marker.exists())
    @unittest.skipUnless(os.name=='posix','POSIX signal integration only')
    def test_cli_sigterm_cleans_descendant(self):
        marker=self.root/'marker';ready=self.root/'ready'
        child="import time,pathlib;time.sleep(1);pathlib.Path(%r).write_text('escaped')"%str(marker)
        self.script("import subprocess,sys,time,pathlib\nsubprocess.Popen([sys.executable,'-c',%r])\npathlib.Path(%r).write_text('ready')\ntime.sleep(10)"%(child,str(ready)),5)
        p=subprocess.Popen([sys.executable,'-m','paper_replay','run',str(self.manifest),'--out',str(self.out),'--allow-execute'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+5
            while not ready.exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(ready.exists());p.send_signal(signal.SIGTERM);stdout,stderr=p.communicate(timeout=5)
            self.assertEqual(p.returncode,143);self.assertNotIn(b'Traceback',stderr);self.assertEqual(stdout,b'');time.sleep(1.1);self.assertFalse(marker.exists());self.assertFalse((self.out/'receipt.json').exists())
        finally:
            if p.poll() is None:p.kill();p.wait()
    @unittest.skipUnless(os.name=='posix','POSIX signal integration only')
    def test_postprocessing_signal_propagates(self):
        self.script("import sys\nopen(sys.argv[1],'w').write('{\"x\":1}')")
        original=core.evaluate
        def inject(*args):os.kill(os.getpid(),signal.SIGTERM);return original(*args)
        with patch.object(core,'evaluate',inject):
            with self.assertRaises(Cancelled):self.run_case()
        self.assertFalse((self.out/'receipt.json').exists())
    @unittest.skipUnless(os.name=='posix','POSIX signal integration only')
    def test_deferred_cleanup_signal_propagates_and_restores_handler(self):
        before=signal.getsignal(signal.SIGTERM)
        with self.assertRaises(Cancelled):
            with cancellation() as state:
                state['cleaning']=True;os.kill(os.getpid(),signal.SIGTERM)
        self.assertEqual(signal.getsignal(signal.SIGTERM),before)
    @unittest.skipUnless(os.name=='posix','POSIX signal integration only')
    def test_signal_during_launch_is_deferred_until_process_known(self):
        from paper_replay import execution
        self.script('import time\ntime.sleep(10)')
        original=execution.subprocess.Popen;children=[]
        def spawn(*args,**kwargs):
            p=original(*args,**kwargs);children.append(p);os.kill(os.getpid(),signal.SIGINT);return p
        with patch.object(execution.subprocess,'Popen',spawn):
            with self.assertRaises(Cancelled):self.run_case()
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll());self.assertFalse((self.out/'receipt.json').exists())
    def test_failed_launch_is_error_not_supported(self):
        from paper_replay import execution
        self.script('pass')
        with patch.object(execution.subprocess,'Popen',side_effect=OSError('synthetic')):
            self.assertEqual(self.run_case()['status'],'execution_error')
