import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from paper_replay.core import run, verify
from paper_replay.private_run import Output

ROOT = Path(__file__).resolve().parents[1]

class RunPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT/'examples/finite_difference', self.root/'project')
        self.manifest = self.root/'project/manifest.json'
        self.out = self.root/'new'/'out'

    def command(self):
        return [sys.executable, '-m', 'paper_replay', 'run', str(self.manifest), '--out', str(self.out), '--allow-execute']

    @unittest.skipUnless(os.name == 'posix', 'POSIX permission modes')
    def test_real_cli_private_modes_and_old_bundle_compatibility(self):
        result = subprocess.run(self.command(), cwd=ROOT, umask=0o022, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o700)
        self.assertEqual(self.out.parent.stat().st_mode & 0o777, 0o700)
        for p in self.out.iterdir():
            self.assertEqual(p.stat().st_mode & 0o777, 0o600, p.name)
            p.chmod(0o644)
        self.out.chmod(0o755)
        verify(self.out)
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.out/'metrics.json').stat().st_mode & 0o777, 0o644)

    @unittest.skipUnless(os.name == 'posix', 'POSIX links')
    def test_dangling_and_existing_output_links_rejected(self):
        self.out.parent.mkdir()
        for target in (self.root/'missing', self.root/'project'):
            self.out.symlink_to(target, target_is_directory=True)
            result = subprocess.run(self.command(), cwd=ROOT, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(self.out.is_symlink())
            self.assertFalse((target/'receipt.json').exists())
            self.out.unlink()
        self.assertFalse((self.root/'missing').exists())

    def test_real_concurrent_run_only_one_winner(self):
        self.out.parent.mkdir()
        children = [subprocess.Popen(self.command(), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
        statuses = []
        for child in children:
            child.communicate(timeout=20)
            statuses.append(child.returncode)
        self.assertEqual(statuses.count(0), 1)
        verify(self.out)

    def test_existing_member_not_overwritten(self):
        output = Output(self.out)
        try:
            output.write('receipt.json', b'user')
            with self.assertRaises(FileExistsError):
                output.write('receipt.json', b'new')
            self.assertEqual((self.out/'receipt.json').read_bytes(), b'user')
        finally:
            output.close()

    def test_exception_preserves_partial_and_closes_descriptor(self):
        closed = []
        original = Output.close
        def close(obj):
            original(obj)
            closed.append(obj.fd)
        with patch.object(Output, 'close', close), patch.object(Output, 'write', side_effect=OSError('injected')):
            with self.assertRaises(OSError):
                run(self.manifest, self.out, execute=True)
        self.assertEqual(closed, [None])
        self.assertTrue(self.out.is_dir())
        self.assertEqual(list(self.out.iterdir()), [])
        with self.assertRaises(Exception):
            run(self.manifest, self.out, execute=True)

    @unittest.skipUnless(os.name == 'posix', 'POSIX directory replacement')
    def test_member_symlink_and_directory_swap_rejected(self):
        output = Output(self.out)
        try:
            target = self.root/'foreign'; target.write_bytes(b'user')
            (self.out/'receipt.json').symlink_to(target)
            with self.assertRaises(FileExistsError):
                output.write('receipt.json', b'new')
            self.out.rename(self.root/'saved')
            self.out.symlink_to(self.root, target_is_directory=True)
            with self.assertRaises(Exception):
                output.write('report.md', b'new')
            self.assertEqual(target.read_bytes(), b'user')
            self.assertFalse((self.root/'report.md').exists())
        finally:
            output.close()
