"""Read-only metric import, without running any project code or DVC commands."""
from pathlib import Path
import hashlib
import re
from .core import (Invalid, VERSION, MAX_BYTES, read_json, parse_json_bytes,
                   write_json, digest, confined, evaluate, validate_claims, render, read_regular, encode_json, same_json)


def load_contract(path):
    c = read_json(path)
    if (not isinstance(c, dict) or type(c.get('schema_version')) is not int
            or c['schema_version'] != 1 or c.get('kind') != 'metric-contract'):
        raise Invalid('expected schema_version 1 metric-contract')
    if set(c) != {'schema_version', 'kind', 'title', 'source', 'claims'}:
        raise Invalid('metric-contract only accepts schema_version, kind, title, source, claims')
    for key in ('title', 'source'):
        if not isinstance(c[key], str) or not c[key].strip():
            raise Invalid(f'{key} must be a non-empty string')
    validate_claims(c['claims'])
    return c


def select_object(document, pointer):
    """RFC 6901 object-key pointer subset. No guessed DVC revisions/file names."""
    if not isinstance(pointer, str) or (pointer and not pointer.startswith('/')):
        raise Invalid('selection must be an empty string or JSON Pointer starting with /')
    selected = document
    if pointer:
        for token in pointer[1:].split('/'):
            if re.search(r'~(?![01])', token):
                raise Invalid('invalid JSON Pointer escape')
            key = token.replace('~1', '/').replace('~0', '~')
            if not isinstance(selected, dict) or key not in selected:
                raise Invalid('selection not found or not an object-key path')
            selected = selected[key]
    if not isinstance(selected, dict):
        raise Invalid('selected metrics must be a JSON object')
    return selected


def aggregate_status(rows):
    statuses = {c['status'] for c in rows}
    return ('insufficient_evidence' if 'insufficient_evidence' in statuses
            else 'not_supported' if 'not_supported' in statuses else 'supported')


def import_metrics(contract_path, metrics_path, output_dir, *, select=''):
    """Read only the named files; write a new evidence bundle. Never execute code."""
    contract = load_contract(Path(contract_path))
    source = Path(metrics_path)
    if not source.is_file():
        raise Invalid('metrics source must be a regular file')
    raw = read_regular(source)
    selected = select_object(parse_json_bytes(raw), select)
    rows = evaluate(contract['claims'], selected)
    out = Path(output_dir).resolve()
    if out.exists():
        raise Invalid('output directory must not exist')
    # Serialize every generated JSON before creating a destination, preventing
    # malformed input/Unicode/depth errors from leaving a misleading partial bundle.
    contract_bytes = encode_json(contract)
    metrics_bytes = encode_json(selected)
    artifacts = {'source-metrics.json': raw, 'metrics.json': metrics_bytes}
    receipt = {'schema_version': 2, 'tool_version': VERSION,
               'title': contract['title'], 'source': contract['source'],
               'evidence_mode': 'imported', 'executed': False,
               'selection': select, 'contract_sha256': hashlib.sha256(contract_bytes).hexdigest(),
               'artifacts': {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()},
               'claims': rows, 'status': aggregate_status(rows)}
    receipt_bytes = encode_json(receipt)
    report = ('# Imported metrics, NOT a rerun\n\n'
              'No experiment or DVC command was executed. Source age, origin, original '
              'execution success and environment were not verified. Hashes only bind the '
              'bytes imported. Inspect the source file before sharing; imports do not redact it.\n\n')
    report_bytes = (report + render(receipt)).encode('utf-8')
    # Filesystem errors (disk full/permissions) can still leave partial output.
    # A receipt is the final file, so absent receipt never signifies completion.
    out.mkdir(parents=True)
    for name, data in {**artifacts, 'contract.json': contract_bytes, 'report.md': report_bytes}.items():
        (out / name).write_bytes(data)
    (out / 'receipt.json').write_bytes(receipt_bytes)
    return receipt


def verify_imported(bundle, receipt):
    """Re-extract the selected metrics as well as recomputing numeric claims."""
    if (type(receipt.get('schema_version')) is not int or receipt['schema_version'] != 2
            or receipt.get('tool_version') != '0.1.2'
            or receipt.get('evidence_mode') != 'imported' or receipt.get('executed') is not False):
        raise Invalid('invalid imported receipt mode/version')
    if set(receipt) != {'schema_version', 'tool_version', 'title', 'source', 'evidence_mode',
                       'executed', 'selection', 'contract_sha256', 'artifacts', 'claims', 'status'}:
        raise Invalid('unexpected imported receipt fields (no execution result is permitted)')
    contract_path = confined(bundle, 'contract.json')
    contract = load_contract(contract_path)
    if (digest(contract_path) != receipt.get('contract_sha256')
            or receipt.get('title') != contract['title'] or receipt.get('source') != contract['source']):
        raise Invalid('contract metadata/digest mismatch')
    artifacts = receipt.get('artifacts')
    if not isinstance(artifacts, dict) or set(artifacts) != {'source-metrics.json', 'metrics.json'}:
        raise Invalid('imported receipt requires source and extracted metrics artifacts')
    for name, expected in artifacts.items():
        path = confined(bundle, name)
        if not path.is_file() or digest(path) != expected:
            raise Invalid(f'artifact digest mismatch: {name}')
    selected = select_object(read_json(confined(bundle, 'source-metrics.json')), receipt.get('selection'))
    # Preserve JSON numeric types when comparing the normalized extraction.
    canonical = encode_json(selected)
    if read_regular(confined(bundle, 'metrics.json')) != canonical:
        raise Invalid('extracted metrics disagree with selected source')
    rows = evaluate(contract['claims'], selected)
    if not same_json(rows, receipt.get('claims')) or aggregate_status(rows) != receipt.get('status'):
        raise Invalid('claim/overall status inconsistent with imported evidence')
    return {'integrity': 'consistent', 'status': receipt['status'], 'evidence_mode': 'imported',
            'executed': False, 'notice': 'Imported bytes only: no execution, source freshness or authenticity verified.'}
