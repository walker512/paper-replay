"""MIT adapter by walker512. Executes reviewed, pinned upstream aggregation.
Not a fresh model rollout or a statistical-design reproduction.
"""
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
module_path = root / 'upstream/tools/reproduce_table1.py'
spec = importlib.util.spec_from_file_location('speceval_aggregate', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
rows = module.compute(root / 'upstream/results/replay')
metrics = {f"b{r['budget']}.{name}": value
           for r in rows for name, value in r.items() if name != 'budget'}
Path(sys.argv[1]).write_text(json.dumps(metrics, indent=2, allow_nan=False) + '\n')
