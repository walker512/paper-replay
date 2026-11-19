import argparse
import json
import sys
from pathlib import Path
from .core import Invalid, load_manifest, check_inputs, run, verify
from .imported import import_metrics
from .execution import Cancelled

def main():
    p = argparse.ArgumentParser(description='Paper Replay Lab: explicit computational claim checks')
    sub = p.add_subparsers(dest='action', required=True)
    v = sub.add_parser('validate'); v.add_argument('manifest')
    r = sub.add_parser('run'); r.add_argument('manifest'); r.add_argument('--out', required=True)
    r.add_argument('--allow-execute', action='store_true', help='Run reviewed local code; NOT sandboxed')
    v = sub.add_parser('verify'); v.add_argument('bundle')
    v.add_argument('--require-supported', action='store_true',
                   help='Exit 2 for consistent but non-supported claims; integrity errors remain exit 1')
    i = sub.add_parser('import-metrics', help='Read existing JSON metrics without executing any code')
    i.add_argument('contract'); i.add_argument('--metrics', required=True); i.add_argument('--out', required=True)
    i.add_argument('--select', default='', help='Explicit JSON Pointer to an object inside an exported JSON file')
    c = sub.add_parser('compare-runs', help='Compare two verified evidence snapshots offline; never execute code')
    c.add_argument('before'); c.add_argument('after'); c.add_argument('--out', required=True)
    c = sub.add_parser('compare-verify'); c.add_argument('bundle')
    c = sub.add_parser('compare-gate', help='Require both snapshots to support unchanged claims')
    c.add_argument('bundle')
    a = p.parse_args()
    try:
        if a.action in ('compare-runs', 'compare-verify', 'compare-gate'):
            from . import comparison
            try:
                if a.action == 'compare-gate':
                    result = comparison.gate(a.bundle)
                elif a.action == 'compare-verify':
                    result = comparison.verify(a.bundle)
                else:
                    result = comparison.build(a.before, a.after, a.out)
            except (ValueError, OSError, KeyError, TypeError, AttributeError, OverflowError, RecursionError):
                print('Error: comparison evidence or output failed validation; private values omitted.', file=sys.stderr)
                return 1
            code = 2 if a.action == 'compare-gate' and not result['passed'] else 0
        elif a.action == 'validate':
            path = Path(a.manifest).resolve(); m = load_manifest(path)
            issues = check_inputs(path.parent, m)
            result = {'valid': not issues, 'input_errors': issues}
            code = 2 if issues else 0
        elif a.action == 'run':
            result = run(a.manifest, a.out, execute=a.allow_execute)
            code = 0 if result['status'] == 'supported' else 2
        elif a.action == 'import-metrics':
            result = import_metrics(a.contract, a.metrics, a.out, select=a.select)
            code = 0 if result['status'] == 'supported' else 2
        else:
            result = verify(a.bundle)
            code = 2 if a.require_supported and result['status'] != 'supported' else 0
        print(json.dumps(result, indent=2, allow_nan=False))
        return code
    except Cancelled as exc:
        print('Experiment cancelled; partial artifacts may remain. No success is returned.',file=sys.stderr)
        return 128+exc.signum
    except (Invalid, ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
