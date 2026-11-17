"""Independent standard-library recomputation of saved objective values.
Checks numerical consistency, not authenticity or proof of execution.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def objective(name,x):
    if len(x)!=5 or not all(type(v) in (float,int) and math.isfinite(v) for v in x):
        raise ValueError('invalid best point')
    if name=='sphere':return math.fsum(v*v for v in x)
    if name!='rotated_quadratic':raise ValueError('unknown objective')
    # Scalar recurrence, independent of the NumPy matrix implementation.
    y=list(x)
    for i in range(4):
        a,b=y[i],y[i+1]
        y[i],y[i+1]=.6*a-.8*b,.8*a+.6*b
    return math.fsum(w*v*v for w,v in zip((1,5,25,125,1000),y))

def verify(directory):
    p=json.loads((ROOT/'protocol.json').read_bytes())
    data=json.loads((directory/'runs.json').read_bytes())
    expected=[(name,seed) for name in p['objectives'] for seed in p['seeds']]
    if [(r['objective'],r['seed']) for r in data['runs']]!=expected:
        raise ValueError('missing, duplicate, reordered or extra run')
    if data['protocol_sha256']!=hashlib.sha256((ROOT/'protocol.json').read_bytes()).hexdigest():
        raise ValueError('protocol mismatch')
    if data['versions']!=p['implementation']:raise ValueError('package version mismatch')
    vals=[];counts=[]
    for r in data['runs']:
        value=objective(r['objective'],r['best_point']); vals.append(value)
        for key in ('best_value','rechecked_value'):
            if not math.isclose(value,r[key],rel_tol=1e-10,abs_tol=1e-15):
                raise ValueError('saved best value disagrees with independent objective evaluation')
        n=r['evaluations'];counts.append(n)
        if type(n) is not int or not 0<n<=p['max_evaluations_per_run']:
            raise ValueError('invalid evaluation count')
        if r['met_target']!=(value<=p['target_value']):raise ValueError('incorrect target status')
        if r['validation_reevaluations']!=1:raise ValueError('invalid reevaluation accounting')
        trace=r['trace']
        if [row['evaluations'] for row in trace]!=list(range(p['population_size'],n+1,p['population_size'])):
            raise ValueError('incomplete evaluation trace')
        bests=[row['best_value'] for row in trace]
        if not bests or not all(type(v) in (float,int) and math.isfinite(v) and v>=0 for v in bests):
            raise ValueError('invalid best trace')
        if any(a<b for a,b in zip(bests,bests[1:])) or bests[-1]!=r['best_value']:
            raise ValueError('inconsistent incumbent trace')
    metrics=json.loads((directory/'metrics.json').read_bytes())
    if metrics['run_count']!=len(expected) or metrics['maximum_evaluations']!=max(counts):
        raise ValueError('summary counts mismatch')
    if metrics['success_fraction']!=sum(v<=p['target_value'] for v in vals)/len(vals):
        raise ValueError('summary success mismatch')
    if not math.isclose(metrics['worst_best_value'],max(vals),rel_tol=1e-10,abs_tol=1e-15):
        raise ValueError('summary value mismatch')
    return {'consistent':True,'runs_checked':len(vals),'all_targets_met':all(v<=p['target_value'] for v in vals)}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('directory',type=Path)
    print(json.dumps(verify(a.parse_args().directory),sort_keys=True))
