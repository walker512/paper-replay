"""Offline comparison of verified snapshots. Never executes experiment code."""
import hashlib
import os
from pathlib import Path
import stat
import tempfile
from . import core

LIMIT = 16 * 1024 * 1024
NAMES = {'receipt.json', 'manifest.json', 'contract.json', 'metrics.json',
         'source-metrics.json', 'stdout.log', 'stderr.log'}
NOTICE = ('Unsigned consistency only, not authenticity, rerun proof or scientific improvement. '
          'Imported metrics are not execution evidence. Missing values are not zero. '
          'Snapshots retain complete selected evidence files; no redaction. '
          'Original report.md is excluded because legacy verification does not bind it.')


def read(path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) |
                 getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0))
    try:
        if Path(path).is_symlink() or not stat.S_ISREG(os.fstat(fd).st_mode):
            raise core.Invalid('Expected ordinary evidence file')
        with os.fdopen(fd, 'rb') as stream:
            fd = None
            raw = stream.read(core.MAX_BYTES + 1)
        if len(raw) > core.MAX_BYTES:
            raise core.Invalid('Evidence file too large')
        return raw
    finally:
        if fd is not None: os.close(fd)


def capture(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise core.Invalid('Expected ordinary evidence directory')
    receipt_bytes = read(root/'receipt.json')
    receipt = core.parse_json_bytes(receipt_bytes)
    if not isinstance(receipt, dict) or not isinstance(receipt.get('artifacts'), dict):
        raise core.Invalid('Invalid receipt structure')
    names = {'receipt.json'} | set(receipt['artifacts'])
    names.add('contract.json' if receipt.get('schema_version') == 2 else 'manifest.json')
    if not names <= NAMES:
        raise core.Invalid('Unexpected evidence member')
    data = {'receipt.json': receipt_bytes}
    for name in sorted(names - {'receipt.json'}): data[name] = read(root/name)
    if sum(map(len, data.values())) > LIMIT:
        raise core.Invalid('Snapshot too large')
    return data


def write_files(root, data):
    root.mkdir(mode=0o700, exist_ok=False)
    for name, raw in sorted(data.items()):
        fd = os.open(root/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                     getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0), 0o600)
        with os.fdopen(fd, 'wb') as stream: stream.write(raw)


def checked(data, root):
    write_files(root, data)
    core.verify(root)  # On the captured bytes, never on live input twice.
    receipt = core.parse_json_bytes(data['receipt.json'])
    imported = receipt['schema_version'] == 2
    declaration = core.parse_json_bytes(data['contract.json' if imported else 'manifest.json'])
    available = receipt['status'] in ('supported', 'not_supported', 'insufficient_evidence')
    metrics = core.parse_json_bytes(data['metrics.json']) if available else {}
    return {'receipt': receipt, 'declaration': declaration, 'metrics': metrics,
            'metrics_evaluated': available, 'mode': 'imported' if imported else 'execution_receipt'}


def value(mapping, key):
    return {'present': key in mapping, 'value': mapping.get(key)}


def changes(left, right):
    return [{'key': k, 'before': value(left,k), 'after': value(right,k)}
            for k in sorted(set(left) | set(right))
            if k not in left or k not in right or not core.same_json(left[k],right[k])]


def analyze(before, after):
    with tempfile.TemporaryDirectory(prefix='paper-compare-') as t:
        a = checked(before, Path(t)/'before'); b = checked(after, Path(t)/'after')
    ac = {c['id']: c for c in a['declaration']['claims']}
    bc = {c['id']: c for c in b['declaration']['claims']}
    rows = []
    warnings = {'No numerical difference or status transition alone establishes improvement.'}
    for ident in sorted(set(ac) | set(bc)):
        x, y = ac.get(ident), bc.get(ident)
        flags = []
        if x is None: flags.append('claim_added')
        elif y is None: flags.append('claim_removed')
        else:
            if not core.same_json(x,y): flags.append('claim_definition_changed')
            if y['absolute_tolerance'] > x['absolute_tolerance']: flags.append('tolerance_widened')
        if flags: warnings.add('Claim set or definition changed; support is not directly comparable.')
        rows.append({'id': ident, 'before': x, 'after': y, 'flags': flags})
    metadata = changes({k:v for k,v in a['declaration'].items() if k!='claims'},
                       {k:v for k,v in b['declaration'].items() if k!='claims'})
    if a['receipt'].get('selection') != b['receipt'].get('selection'):
        warnings.add('Imported selection changed; selected scopes are not necessarily comparable.')
    if a['mode'] != b['mode']: warnings.add('Evidence mode changed: import and execution receipts are different evidence.')
    if a['mode'] == 'imported' or b['mode'] == 'imported':
        warnings.add('Imported source freshness, provenance, inputs and execution are unknown.')
    if any(x['key'] in ('inputs','command','timeout_seconds') for x in metadata):
        warnings.add('Declared inputs, entry script, command or timeout changed; no direct improvement attribution.')
    if not a['metrics_evaluated'] or not b['metrics_evaluated']:
        warnings.add('At least one run did not evaluate metrics; any retained metrics are not treated as successful evidence.')
    def side(s, raw):
        declaration = s['declaration']
        inputs = declaration.get('inputs') if s['mode']=='execution_receipt' else None
        script = declaration['command'][1] if inputs is not None else None
        return {'mode': s['mode'], 'status': s['receipt']['status'],
                'metrics_evaluated': s['metrics_evaluated'],
                'input_sha256_declarations': inputs,
                'entry_script': script, 'entry_script_sha256_declaration': inputs.get(script) if inputs else None,
                'receipt_claim_results': s['receipt']['claims'],
                'selection':s['receipt'].get('selection'),
                'environment_declaration':s['receipt'].get('environment'),
                'evidence_sha256': {n:hashlib.sha256(v).hexdigest() for n,v in sorted(raw.items())}}
    result = {'schema_version':1,'kind':'run-comparison', 'before':side(a,before), 'after':side(b,after),
              'claim_changes':rows,'declaration_changes':metadata,
              'metric_changes':changes(a['metrics'],b['metrics']),
              'improvement_established':False, 'warnings':sorted(warnings), 'notice':NOTICE}
    return core.encode_json(result)


def build(before, after, out):
    a, b = capture(before), capture(after)
    report = analyze(a,b)
    root = Path(out); root.mkdir(mode=0o700, exist_ok=False)
    write_files(root/'before',a); write_files(root/'after',b)
    # Completion file last; partial outputs are intentionally not deleted/reused.
    fd = os.open(root/'comparison.json', os.O_WRONLY|os.O_CREAT|os.O_EXCL|
                 getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_BINARY',0),0o600)
    with os.fdopen(fd,'wb') as stream: stream.write(report)
    return {'consistent':True,'improvement_established':False,'notice':NOTICE}


def _verified_report(folder):
    root = Path(folder)
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != {'before','after','comparison.json'}:
        raise core.Invalid('Unexpected comparison bundle')
    a,b = capture(root/'before'),capture(root/'after')
    for name, data in (('before',a),('after',b)):
        if {p.name for p in (root/name).iterdir()} != set(data):
            raise core.Invalid('Unexpected snapshot member')
    report = read(root/'comparison.json')
    if report != analyze(a,b):
        raise core.Invalid('Comparison differs from recomputation')
    return report


def verify(folder):
    _verified_report(folder)
    return {'consistent':True,'improvement_established':False,'notice':NOTICE}


def gate(folder):
    """Check a verified comparison against a stable-claims policy."""
    report = core.parse_json_bytes(_verified_report(folder))
    before, after = report['before'], report['after']
    reasons = []
    if before['status'] != 'supported':
        reasons.append('baseline_not_supported')
    if after['status'] != 'supported':
        reasons.append('candidate_not_supported')
    if any(row['flags'] for row in report['claim_changes']):
        reasons.append('claims_changed')
    if before['mode'] != after['mode']:
        reasons.append('evidence_mode_changed')
    elif before['mode'] == 'imported' and before['selection'] != after['selection']:
        reasons.append('import_selection_changed')
    return {'schema_version': 1, 'kind': 'stable-claims-gate',
            'consistent': True, 'passed': not reasons, 'reasons': reasons,
            'improvement_established': False}
