# Fresh CMA-ES method experiment, followed by non-executing import

**Scope:** original, preselected synthetic objectives using the official paper-associated implementation. This is NOT a reproduction of the tutorial's tables, a full external paper replication, an optimizer ranking or proof that Paper Replay is superior.

Reference: Nikolaus Hansen, [The CMA Evolution Strategy: A Tutorial, arXiv:1604.00772v2](https://arxiv.org/abs/1604.00772v2). Official [CMA-ES implementation](https://github.com/CMA-ES/pycma), version `cma==4.4.0`, BSD-3-Clause. NumPy `2.2.6` distribution notices are retained. The tutorial is linked, not redistributed. Original adapter, synthetic data/protocol and checker are MIT, walker512.

## What is computed

Six fresh ask/evaluate/tell optimizer runs: sphere and a fixed rotated quadratic (positive weights 1, 5, 25, 125, 1000), five dimensions, seeds 7/42/2026, start [3,3,3,3,3], sigma 1, population 10. Preselected acceptance: each final objective <=1e-8 within 4000 optimization calls. Protocol/source hashes were locally recorded before the first observed run, but that record is not independently authenticated preregistration. No parameter, seed or threshold was changed after results.

The optimizer actually evaluates candidate points. No author result table is read. The independent scalar checker recomputes each final objective without the NumPy matrix code, checks trace and budget consistency, and validates summaries. Saved JSON is unsigned: a fabricated but consistent result cannot be authenticated by arithmetic alone.

## Execute reviewed code (Linux CPython 3.12 measured)

These explicit steps execute trusted local sample code and install official PyPI dependencies. They are **separate from** Paper Replay's non-executing import. Review the code first. No sandbox is provided.

From this example directory:

```sh
python -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-linux-cp312-hashes.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python experiment.py --out fresh-run
.venv/bin/python make_snapshot.py fresh-run --out fresh-evidence.json
```

`make_snapshot.py` runs the independent scalar verifier once and embeds the complete protocol, per-run traces, metrics and call accounting into one source JSON. Its snapshot import is not a second optimizer execution.

In the original six cases: optimizer calls total 5580; the experiment internally reevaluates six final points with its own objective; the snapshot verifier independently evaluates six points. **5580 + 6 + 6 = 5592 objective calls** for experiment plus one verifier. Running extra checkers adds extra calls; this is not a lifetime count. Internal `rechecked_value` uses the same implementation; independence comes from `verify_results.py`.

The exact wheel hash lock is only for Linux x86_64 CPython 3.12; `requirements.txt` pins versions but is NOT a portable binary lock. Other platforms have not been validated for this method trial. A missing optional matplotlib warning is harmless because no plotting occurs.

## Import saved results without running an experiment

Use Paper Replay 0.1.2 or later from its installed environment; it does not need cma or NumPy:

```sh
paper-replay import-metrics import-contract.json --metrics fresh-evidence.json --select /metrics --out imported-receipt
paper-replay verify imported-receipt
```

The receipt explicitly says `evidence_mode=imported`, `executed=false`. The entire source JSON (including traces) is hash-bound, not merely flat metrics. Paper Replay verifies byte consistency, extraction and numeric assertions; **it does not run the optimizer or the independent scalar checker during import/verify**. The included saved numerical fixtures are original synthetic records; your new local results are not uploaded automatically.

## Observed verification

The original and repeated runs attained all six thresholds in 750–1120 optimization evaluations per case; worst final objective 9.177137409080747e-9. An independent reviewer reran all six, obtained byte-identical saved JSON in the same pinned environment, passed eight sample tests and checked wheel/license/source hashes. This is local deterministic repeatability, not an estimate of general stochastic success.

`run-first` and `run-repeat` are recorded outputs for test regressions, clearly separate from `fresh-run`. From this directory, `.venv/bin/python -m unittest -v test_experiment` checks objectives, missing runs, wrong points, budgets, success flags and recorded-repeat consistency. These tests do not themselves execute a fresh optimization run.

No claim is made that CMA-ES is best on these simple convex functions or that method verification reproduces the tutorial's empirical claims. The protocol's purpose is to exercise a genuine numerical workflow with explicit verification boundaries.

Independent integration review rebuilt the snapshot, verified byte equality to the imported source, checked the 5592 accounting and reran non-executing import/verification. Following review, the import-claim statements distinguish responsibilities: the experiment performs optimization; the separate sample checker checks saved numerical results, objective/seed identities and budget accounting **before import**, but does not authenticate execution; Paper Replay checks imported fields and evidence consistency only. The revised contract was re-imported and verified successfully without rerunning the optimizer.
