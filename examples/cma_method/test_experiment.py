import copy,json,math,shutil,tempfile,unittest
from pathlib import Path
import experiment
import verify_results as checker

class Checks(unittest.TestCase):
    def test_independent_objectives(self):
        for x in ([0]*5,[3]*5,[1,-2,3,-4,5],[-.001,2.5,3.14,0,9]):
            for name in ('sphere','rotated_quadratic'):
                self.assertTrue(math.isclose(experiment.objective(name,x),checker.objective(name,x),rel_tol=1e-14,abs_tol=1e-12))
    def test_analytic_zero(self):
        for name in ('sphere','rotated_quadratic'):self.assertEqual(checker.objective(name,[0]*5),0)
    def test_valid_saved_runs(self):
        self.assertTrue(checker.verify(Path('run-first'))['all_targets_met'])
    def test_bad_point_rejected(self):
        self.mutate(lambda d:d['runs'][0].update(best_point=[3]*5))
    def test_missing_run_rejected(self):
        self.mutate(lambda d:d['runs'].pop())
    def test_false_count_rejected(self):
        self.mutate(lambda d:d['runs'][0].update(evaluations=999999))
    def test_false_success_rejected(self):
        self.mutate(lambda d:d['runs'][0].update(met_target=False))
    def mutate(self,fn):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'run';shutil.copytree('run-first',p)
            d=json.loads((p/'runs.json').read_bytes());fn(d)
            (p/'runs.json').write_text(json.dumps(d))
            with self.assertRaises(ValueError):checker.verify(p)
    def test_same_seed_repeat_local(self):
        a=json.loads(Path('run-first/runs.json').read_bytes())
        b=json.loads(Path('run-repeat/runs.json').read_bytes())
        self.assertEqual(a,b)

if __name__=='__main__':unittest.main()
