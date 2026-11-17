"""Original MIT adapter by walker512. Bundle validated saved outputs; do not rerun."""
import argparse
import json
from pathlib import Path
import verify_results

ROOT=Path(__file__).resolve().parent

def make_snapshot(run_dir, destination):
    verified=verify_results.verify(run_dir)
    if not verified['consistent']:
        raise ValueError('numerically inconsistent results')
    runs=json.loads((run_dir/'runs.json').read_bytes())
    optimizer_calls=sum(r['evaluations'] for r in runs['runs'])
    internal_calls=sum(r['validation_reevaluations'] for r in runs['runs'])
    independent_calls=len(runs['runs'])  # verify_results above recomputed each objective.
    snapshot={'protocol':json.loads((ROOT/'protocol.json').read_bytes()),
              'run_evidence':runs,'metrics':json.loads((run_dir/'metrics.json').read_bytes()),
              'accounting':{'optimization_calls':optimizer_calls,'internal_reevaluations':internal_calls,
                            'independent_scalar_checks_in_this_snapshot_step':independent_calls,
                            'experiment_plus_one_verification':optimizer_calls+internal_calls+independent_calls}}
    # This is not a lifetime total if users ran other verification commands.
    raw=(json.dumps(snapshot,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    with destination.open('xb') as file:
        file.write(raw)
    return snapshot

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run_dir',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();make_snapshot(a.run_dir,a.out)
