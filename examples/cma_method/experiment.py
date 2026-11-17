"""MIT sample by walker512. Fresh official pycma ask/tell experiment.
Protocol and thresholds are selected before observing the first experiment.
No paper tables, cached measurements, private data or external APIs are read.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import numpy as np
import cma

ROOT = Path(__file__).resolve().parent

def dump(path, obj):
    path.write_bytes((json.dumps(obj, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())

def rotation():
    q = np.eye(5)
    for i in range(4):
        g = np.eye(5)
        g[i,i] = g[i+1,i+1] = 3/5
        g[i,i+1] = -4/5
        g[i+1,i] = 4/5
        q = g @ q
    return q

Q = rotation()
WEIGHTS = np.array([1,5,25,125,1000], dtype=float)

def objective(name, x):
    x = np.asarray(x, dtype=float)
    if x.shape != (5,) or not np.isfinite(x).all():
        raise ValueError('expected five finite coordinates')
    if name == 'sphere':
        return float(x @ x)
    if name == 'rotated_quadratic':
        y = Q @ x
        return float(y @ (WEIGHTS * y))
    raise ValueError('unknown objective')

def one_run(name, seed, protocol):
    es = cma.CMAEvolutionStrategy(protocol['initial_point'], protocol['sigma0'], {
        'seed':seed, 'popsize':protocol['population_size'],
        'maxfevals':protocol['max_evaluations_per_run'],
        'ftarget':protocol['target_value'], 'verbose':-9,
        'verb_log':0, 'verb_disp':0, 'verb_time':False,
    })
    best = float('inf'); best_x = None; count = 0; trace = []
    while not es.stop():
        if count + es.popsize > protocol['max_evaluations_per_run']:
            break
        candidates = es.ask()
        values = [objective(name,x) for x in candidates]
        count += len(values)
        k = int(np.argmin(values))
        if values[k] < best:
            best = values[k]; best_x = candidates[k].tolist()
        es.tell(candidates, values)
        trace.append({'evaluations': count, 'best_value': best})
    if best_x is None:
        raise RuntimeError('optimizer never evaluated a candidate')
    rechecked = objective(name,best_x)
    return {'objective':name,'seed':seed,'evaluations':count,'best_value':best,
            'best_point':best_x,'validation_reevaluations':1,'rechecked_value':rechecked,
            'met_target':rechecked <= protocol['target_value'], 'trace':trace,
            'stop_reasons':{str(k):str(v) for k,v in es.stop().items()}}

def run(output):
    protocol = json.loads((ROOT/'protocol.json').read_bytes())
    versions = {n:importlib.metadata.version(n) for n in ('cma','numpy')}
    if versions != protocol['implementation']:
        raise RuntimeError(f'expected pinned packages {protocol["implementation"]}, got {versions}')
    if output.exists():
        raise FileExistsError('use a fresh output directory')
    output.mkdir(parents=True)
    runs = [one_run(name,seed,protocol) for name in protocol['objectives'] for seed in protocol['seeds']]
    metrics = {'success_fraction':sum(r['met_target'] for r in runs)/len(runs),
               'worst_best_value':max(r['rechecked_value'] for r in runs),
               'maximum_evaluations':max(r['evaluations'] for r in runs),
               'run_count':len(runs)}
    dump(output/'runs.json',{'protocol_sha256':hashlib.sha256((ROOT/'protocol.json').read_bytes()).hexdigest(),
                            'versions':versions,'python':platform.python_version(),'runs':runs})
    dump(output/'metrics.json',metrics)
    print(json.dumps(metrics,sort_keys=True))
    return 0 if metrics['success_fraction'] == 1 else 2

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path)
    raise SystemExit(run(p.parse_args().out))
