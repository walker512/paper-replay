"""Deterministic claim checking. This is not an execution sandbox."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import stat
import sys
import time

VERSION = '0.1.2'
SUPPORTED_TOOL_VERSIONS = ('0.1.0', '0.1.1', VERSION)
MAX_BYTES = 2_000_000
MAX_JSON_DEPTH = 64
MAX_EVIDENCE_BYTES = 64 * 1024 * 1024

class Invalid(ValueError):
    pass


def open_regular(path, limit):
    """Open without FIFO blocking; check the opened descriptor, not just a path."""
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise Invalid('input must be a regular file')
        if info.st_size > limit:
            raise Invalid(f'file exceeds {limit}-byte limit')
        return os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise


def read_regular(path, limit=MAX_BYTES):
    with open_regular(path, limit) as file:
        raw = file.read(limit + 1)
    if len(raw) > limit:
        raise Invalid(f'file exceeds {limit}-byte limit')
    return raw


def validate_json_tree(value):
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise Invalid(f'JSON nesting exceeds depth {MAX_JSON_DEPTH}')
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise Invalid('JSON object keys must be strings')
                try:
                    key.encode('utf-8')
                except UnicodeError as exc:
                    raise Invalid('JSON contains an invalid Unicode surrogate') from exc
                stack.append((child, depth + 1))
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            try:
                item.encode('utf-8')
            except UnicodeError as exc:
                raise Invalid('JSON contains an invalid Unicode surrogate') from exc
        elif isinstance(item, float) and not math.isfinite(item):
            raise Invalid('JSON contains a non-finite number')


def read_json(path):
    return parse_json_bytes(read_regular(path))


def parse_json_bytes(raw):
    if len(raw) > MAX_BYTES:
        raise Invalid('JSON exceeds 2 MB limit')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Invalid(f'duplicate JSON key: {key}')
            result[key] = value
        return result
    def nonfinite(value):
        raise Invalid(f'non-finite JSON: {value}')
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise Invalid('JSON decimal is outside supported finite floating-point range')
        return result
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                           parse_constant=nonfinite, parse_float=finite_float)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Invalid(f'invalid JSON: {exc.__class__.__name__}') from exc
    validate_json_tree(value)
    return value


def digest(path):
    hasher = hashlib.sha256()
    with open_regular(path, MAX_EVIDENCE_BYTES) as file:
        count = 0
        while block := file.read(65536):
            count += len(block)
            if count > MAX_EVIDENCE_BYTES:
                raise Invalid('evidence exceeds 64 MiB limit')
            hasher.update(block)
    return hasher.hexdigest()


def encode_json(value):
    """Deterministic UTF-8/LF metadata, not RFC 8785 canonical JSON."""
    validate_json_tree(value)
    try:
        encoded = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False,
                              allow_nan=False) + '\n').encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise Invalid('JSON cannot be serialized safely') from exc
    if len(encoded) > MAX_BYTES:
        raise Invalid('serialized JSON exceeds 2 MB limit')
    return encoded


def write_json(path, value):
    path.write_bytes(encode_json(value))


def same_json(left, right):
    """Strict serialized equality: JSON true must not masquerade as numeric 1."""
    return encode_json(left) == encode_json(right)


def confined(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise Invalid('paths must be non-empty relative paths')
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise Invalid(f'path escapes project: {value}')
    return path


def number(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def load_manifest(path):
    m = read_json(path)
    if not isinstance(m, dict) or type(m.get('schema_version')) is not int or m['schema_version'] != 1:
        raise Invalid('expected schema_version 1 object')
    for key in ('title', 'source'):
        if not isinstance(m.get(key), str) or not m[key].strip():
            raise Invalid(f'{key} must be a non-empty string')
    inputs = m.get('inputs')
    if not isinstance(inputs, dict) or not inputs:
        raise Invalid('inputs must pin at least one file with SHA-256')
    for name, sha in inputs.items():
        confined(path.parent, name)
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise Invalid(f'invalid SHA-256 for {name}')
    command = m.get('command')
    if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x for x in command):
        raise Invalid('command must be a non-empty argv list')
    if command[0] != '{python}':
        raise Invalid('prototype commands must start with {python}')
    if len(command) < 2 or command[1].startswith('-') or command[1] not in inputs:
        raise Invalid('Python entry script must be an explicitly pinned input')
    timeout = m.get('timeout_seconds', 30)
    if not number(timeout) or not 0 < timeout <= 300:
        raise Invalid('timeout_seconds must be in (0, 300]')
    if m.get('metrics') != '{output}':
        raise Invalid('metrics must be {output}; runner supplies fresh path')
    if '{output}' not in command:
        raise Invalid('command must contain {output} argument')
    validate_claims(m.get('claims'))
    return m


def validate_claims(claims):
    if not isinstance(claims, list) or not claims:
        raise Invalid('claims must be a non-empty list')
    ids = set()
    for c in claims:
        if not isinstance(c, dict):
            raise Invalid('claim must be an object')
        for key in ('id', 'statement', 'metric'):
            if not isinstance(c.get(key), str) or not c[key].strip():
                raise Invalid(f'claim {key} must be a non-empty string')
        if c['id'] in ids:
            raise Invalid('duplicate claim id')
        ids.add(c['id'])
        if not number(c.get('expected')):
            raise Invalid('expected must be finite numeric')
        if not number(c.get('absolute_tolerance')) or c['absolute_tolerance'] < 0:
            raise Invalid('absolute_tolerance must be finite and non-negative')


def evaluate(claims, metrics):
    if not isinstance(metrics, dict):
        raise Invalid('metrics must be a JSON object')
    results = []
    for claim in claims:
        metric = claim['metric']
        value = metrics.get(metric)
        row = dict(claim)
        if metric not in metrics or not number(value):
            row.update(status='insufficient_evidence', observed=None,
                       reason='missing or non-finite/non-numeric metric')
        else:
            error = abs(value - claim['expected'])
            row.update(status='supported' if error <= claim['absolute_tolerance'] else 'not_supported',
                       observed=value, absolute_error=error if number(error) else None)
            if not number(error):
                row['reason'] = 'absolute error exceeds floating-point range'
        results.append(row)
    return results


def check_inputs(root, manifest):
    problems = []
    for name, expected in manifest['inputs'].items():
        path = confined(root, name)
        if not path.is_file():
            problems.append({'path': name, 'reason': 'missing'})
        elif digest(path) != expected:
            problems.append({'path': name, 'reason': 'hash_mismatch'})
    return problems


def run(manifest_path, output_dir, *, execute=False):
    """Run only a user-reviewed local script. Hashes establish identity, not trust."""
    manifest_path = Path(manifest_path).resolve()
    m = load_manifest(manifest_path)
    root = manifest_path.parent
    out = Path(output_dir).resolve()
    if out.exists():
        raise Invalid('output directory must not exist (prevents stale metrics/replacing evidence)')
    if not execute:
        raise Invalid('execution requires --allow-execute after reviewing the pinned script')
    out.mkdir(parents=True)
    # Keep a source manifest so receipts can be checked without external state.
    write_json(out / 'manifest.json', m)
    receipt = {'schema_version': 1, 'tool_version': VERSION, 'title': m['title'],
               'source': m['source'], 'manifest_sha256': digest(out / 'manifest.json'),
               'environment': {'python': platform.python_version(), 'platform': platform.system()},
               'claims': [], 'status': 'execution_error', 'artifacts': {}}
    before = check_inputs(root, m)
    if before:
        receipt.update(status='input_mismatch', input_errors=before)
    else:
        metrics_path = out / 'metrics.json'
        command = [sys.executable if arg == '{python}' else str(metrics_path) if arg == '{output}' else arg for arg in m['command']]
        command[1] = str(confined(root, m['command'][1]))
        started = time.monotonic()
        # Logs stay local; no environment variables or absolute command paths in receipt.
        with (out / 'stdout.log').open('wb') as stdout, (out / 'stderr.log').open('wb') as stderr:
            try:
                result = subprocess.run(command, cwd=root, stdout=stdout, stderr=stderr,
                                        timeout=m.get('timeout_seconds', 30), check=False,
                                        env={'PATH': os.defpath, 'PYTHONHASHSEED': '0',
                                             'PYTHONIOENCODING': 'utf-8'})
                receipt['exit_code'] = result.returncode
                after = check_inputs(root, m)
                if after:
                    receipt.update(status='input_mismatch', input_errors=after)
                elif result.returncode != 0:
                    receipt['error'] = 'experiment exited nonzero; metrics not evaluated'
                elif not metrics_path.is_file() or metrics_path.is_symlink():
                    receipt['error'] = 'experiment did not create a regular metrics file'
                else:
                    receipt['claims'] = evaluate(m['claims'], read_json(metrics_path))
                    statuses = {c['status'] for c in receipt['claims']}
                    receipt['status'] = ('insufficient_evidence' if 'insufficient_evidence' in statuses
                                         else 'not_supported' if 'not_supported' in statuses else 'supported')
            except subprocess.TimeoutExpired:
                receipt['error'] = 'experiment timed out; metrics not evaluated'
            except (Invalid, ValueError, OSError) as exc:
                receipt['error'] = f'metrics or execution error: {type(exc).__name__}'
        receipt['duration_seconds'] = round(time.monotonic() - started, 6)
        for name in ('metrics.json', 'stdout.log', 'stderr.log'):
            file = out / name
            if file.is_file() and not file.is_symlink():
                receipt['artifacts'][name] = digest(file)
    write_json(out / 'receipt.json', receipt)
    (out / 'report.md').write_bytes(render(receipt).encode('utf-8'))
    return receipt


def render(receipt):
    title = str(receipt['title']).replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')
    lines = [f"# {title}", '', f"Status: **{receipt['status']}**", '',
             'This checks declared numerical claims, not scientific truth or paper validity.', '',
             '| Claim | Metric | Observed | Expected ± absolute tolerance | Status |',
             '|---|---|---|---|---|']
    def safe(value):
        return str(value).replace('|', '\\|').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')
    for row in receipt['claims']:
        lines.append('| ' + ' | '.join(safe(x) for x in (row['id'], row['metric'], row['observed'],
                     f"{row['expected']} ± {row['absolute_tolerance']}", row['status'])) + ' |')
    return '\n'.join(lines) + '\n'


def verify(bundle):
    """Verify self-consistency, not identity/authenticity: receipts are not signed."""
    bundle = Path(bundle).resolve()
    receipt = read_json(bundle / 'receipt.json')
    if isinstance(receipt, dict) and receipt.get('schema_version') == 2:
        from .imported import verify_imported
        return verify_imported(bundle, receipt)
    manifest = load_manifest(bundle / 'manifest.json')
    if (not isinstance(receipt, dict) or type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 1
            or receipt.get('tool_version') not in SUPPORTED_TOOL_VERSIONS
            or receipt.get('title') != manifest['title']
            or receipt.get('source') != manifest['source']):
        raise Invalid('receipt metadata inconsistent with manifest or supported schema')
    if digest(bundle / 'manifest.json') != receipt.get('manifest_sha256'):
        raise Invalid('manifest digest mismatch')
    artifacts = receipt.get('artifacts')
    if not isinstance(artifacts, dict):
        raise Invalid('invalid artifact list')
    for name, expected in artifacts.items():
        if name not in ('metrics.json', 'stdout.log', 'stderr.log'):
            raise Invalid('unexpected artifact')
        path = confined(bundle, name)
        if not path.is_file() or digest(path) != expected:
            raise Invalid(f'artifact digest mismatch: {name}')
    status = receipt.get('status')
    if status in ('supported', 'not_supported', 'insufficient_evidence'):
        if 'metrics.json' not in artifacts:
            raise Invalid('missing metrics artifact')
        rows = evaluate(manifest['claims'], read_json(bundle / 'metrics.json'))
        statuses = {c['status'] for c in rows}
        actual = ('insufficient_evidence' if 'insufficient_evidence' in statuses
                  else 'not_supported' if 'not_supported' in statuses else 'supported')
        if (not same_json(rows, receipt.get('claims')) or actual != status
                or type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0):
            raise Invalid('claim/overall status inconsistent with evidence')
    elif status not in ('input_mismatch', 'execution_error') or receipt.get('claims'):
        raise Invalid('invalid failure receipt')
    return {'integrity': 'consistent', 'status': status,
            'notice': 'Unsigned bundle: consistency is not authenticity or scientific validation.'}
