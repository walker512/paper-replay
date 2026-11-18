import os
import stat
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from paper_replay.core import Invalid, verify, write_json
from paper_replay.imported import import_metrics

class PrivateImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.contract = self.root / 'contract.json'
        self.source = self.root / 'source.json'
        self.out = self.root / 'out'
        write_json(self.contract, {'schema_version': 1, 'kind': 'metric-contract',
            'title': 'Synthetic', 'source': 'Synthetic only', 'claims': [
            {'id': 'x', 'statement': 'one', 'metric': 'x', 'expected': 1, 'absolute_tolerance': 0}]})
        write_json(self.source, {'x': 1, 'private': 'SYNTHETIC_ONLY'})
    def tearDown(self):
        self.temp.cleanup()
    def run_import(self):
        return import_metrics(self.contract, self.source, self.out)
    @unittest.skipUnless(os.name == 'posix', 'POSIX modes, not Windows ACL assurance')
    def test_private_at_creation_under_permissive_umask(self):
        real_open = os.open
        modes = []
        def checked_open(path, flags, mode=0o777, **kw):
            fd = real_open(path, flags, mode, **kw)
            if flags & os.O_CREAT:
                modes.append(stat.S_IMODE(os.fstat(fd).st_mode))
                self.assertEqual(stat.S_IMODE(self.out.stat().st_mode), 0o700)
                self.assertTrue(flags & os.O_EXCL)
            return fd
        self.out = self.root / 'new-parent' / 'new-child' / 'out'
        previous = os.umask(0)
        try:
            with patch('paper_replay.imported.os.open', side_effect=checked_open):
                self.run_import()
        finally:
            os.umask(previous)
        self.assertEqual(modes, [0o600] * 5)
        for p in (self.out, self.out.parent, self.out.parent.parent):
            self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o700)
        self.assertEqual(verify(self.out)['status'], 'supported')
    def test_concurrent_same_destination_exactly_one_success(self):
        barrier = threading.Barrier(2)
        def attempt():
            barrier.wait()
            try:
                self.run_import()
                return True
            except (Invalid, OSError):
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(verify(self.out)['status'], 'supported')
    @unittest.skipUnless(os.name == 'posix', 'symlink creation may require Windows privilege')
    def test_dangling_output_symlink_rejected(self):
        target = self.root / 'target'
        self.out.symlink_to(target, target_is_directory=True)
        with self.assertRaises((Invalid, OSError)):
            self.run_import()
        self.assertFalse(target.exists())
    @unittest.skipUnless(os.name == 'posix', 'POSIX link injection')
    def test_injected_file_symlink_never_overwritten(self):
        target = self.root / 'sentinel'
        target.write_bytes(b'unchanged')
        real_open = os.open
        def injecting_open(path, flags, mode=0o777, **kw):
            if flags & os.O_CREAT and str(path) == 'source-metrics.json':
                (self.out / 'source-metrics.json').symlink_to(target)
            return real_open(path, flags, mode, **kw)
        with patch('paper_replay.imported.os.open', side_effect=injecting_open):
            with self.assertRaises(OSError):
                self.run_import()
        self.assertEqual(target.read_bytes(), b'unchanged')
        self.assertFalse((self.out / 'receipt.json').exists())
    def test_failure_keeps_partial_files_private_no_receipt(self):
        real_open = os.open
        def failing_open(path, flags, mode=0o777, **kw):
            if flags & os.O_CREAT and Path(path).name == 'metrics.json':
                raise OSError('synthetic disk failure')
            return real_open(path, flags, mode, **kw)
        with patch('paper_replay.imported.os.open', side_effect=failing_open):
            with self.assertRaises(OSError):
                self.run_import()
        self.assertFalse((self.out / 'receipt.json').exists())
        if os.name == 'posix':
            self.assertEqual(stat.S_IMODE((self.out / 'source-metrics.json').stat().st_mode), 0o600)
        with self.assertRaises((Invalid, OSError)):
            verify(self.out)
    def test_existing_output_and_parent_permissions_unchanged(self):
        self.out.mkdir()
        sentinel = self.out / 'source-metrics.json'
        sentinel.write_bytes(b'unchanged')
        before = self.root.stat().st_mode
        with self.assertRaises((Invalid, OSError)):
            self.run_import()
        self.assertEqual(sentinel.read_bytes(), b'unchanged')
        self.assertEqual(self.root.stat().st_mode, before)
    @unittest.skipUnless(os.name == 'posix', 'POSIX directory-fd protection')
    def test_output_directory_replacement_rejected(self):
        moved = self.root / 'moved'
        external = self.root / 'external'
        external.mkdir()
        real_open = os.open
        def replacing_open(path, flags, mode=0o777, **kw):
            fd = real_open(path, flags, mode, **kw)
            if flags & getattr(os, 'O_DIRECTORY', 0) and Path(path) == self.out:
                self.out.rename(moved)
                self.out.symlink_to(external, target_is_directory=True)
            return fd
        with patch('paper_replay.imported.os.open', side_effect=replacing_open):
            with self.assertRaises(Invalid):
                self.run_import()
        self.assertEqual(list(external.iterdir()), [])
        self.assertFalse((moved / 'receipt.json').exists())
    def test_receipt_creation_failure_does_not_claim_completion(self):
        real_open = os.open
        def failing_open(path, flags, mode=0o777, **kw):
            if flags & os.O_CREAT and Path(path).name == 'receipt.json':
                raise OSError('synthetic receipt failure')
            return real_open(path, flags, mode, **kw)
        with patch('paper_replay.imported.os.open', side_effect=failing_open):
            with self.assertRaises(OSError):
                self.run_import()
        self.assertFalse((self.out / 'receipt.json').exists())
        with self.assertRaises((Invalid, OSError)):
            verify(self.out)
