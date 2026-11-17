# Paper Replay Lab competitor baseline (local, unpublished)

Author: walker512. This is a workflow baseline, not a winner ranking.

## Environment and provenance

- Python 3.12.14, Linux 6.18.57 x86_64.
- Official PyPI packages: DVC 3.67.1, ReproZip 1.3.2; package lock snapshot in `logs/packages-final.stdout`.
- Original MIT numerical experiment copied unchanged from Paper Replay Lab `examples/finite_difference/experiment.py`; exact copy `source-experiment.py`, SHA-256 `source-sha256.txt`.
- DVC configured with `init --no-scm`, one stage, pinned dependency `experiment.py`, metrics output `metrics.json`. This intentionally does not exercise Git experiment branches, cloud storage, or remote reproduction.
- Raw commands, exit codes, elapsed times and working directories: `commands.json`. stdout/stderr by command label: `logs/`. Installation logs retained. Runners: `run_baselines.py`, `retry_reprozip.py`.
- Raw evidence is retained privately. Historical selected command records were sanitized for local review; these logs are excluded from this source distribution. No remote repositories or services were created during baseline measurement.

## DVC: actual results

| Scenario | Observation | Interpretation |
|---|---|---|
| First `dvc repro` | exit 0; expected finite-difference metrics produced | Successful numerical execution |
| Unchanged `dvc repro` | exit 0; stage skipped as unchanged | Successful cache/dependency behavior, not a fresh numerical rerun |
| `dvc repro --force` | exit 0; experiment executed | Successful repeated execution |
| `dvc metrics show --json` | exit 0; metrics displayed | Existing metric inspection capability |
| Change fine step from .01 to .005 | exit 0; dependency change triggers rerun and lock update | Correct DVC behavior; changed experiment intentionally accepted |
| Script exits 7 | DVC exit 255, explicit underlying exit 7 error | Correct execution failure detection |
| Script exits 0 but produces no metrics | DVC exit 255, output does not exist | Correct missing-output detection |
| Restore original script and force run | exit 0 | Baseline working copy restored |

Baseline metrics: error ratio 3.9999400004923804, estimated order 1.9999783595896732.
Changed-input metrics: error ratio 15.99970001294935, estimated order 3.999972950382026.

The change deliberately invalidates the specific claim that the two selected steps differ by a factor of two. DVC rerunning and recording new metrics is **not a false pass or defect**: no numerical claim assertion was configured in its stage. DVC can execute a checker or integrate the proposed claim layer. Paper Replay Lab's narrower proposed value is packaging an explicit claim contract and an offline consistency report, not superior experiment execution. Input hash refusal and DVC dependency rerun are different policies, not directly comparable success metrics.

## ReproZip: installation repaired, execution blocked by environment

1. Initial installed ReproZip failed before CLI startup: `ModuleNotFoundError: No module named 'distutils'` under Python 3.12.
2. Installed official `setuptools==84.2.1` into the isolated venv. ReproZip version command then succeeded.
3. Set HOME to the baseline-local `home/`; successfully disabled ReproZip usage reporting. No security policy changes attempted.
4. All five independent trace scenarios (original, repeated, changed input, nonzero exit, missing output) exited 125 with:

```
CRITICAL: couldn't use ptrace: Operation not permitted
```

This is a host isolation restriction. The experiment did not execute under tracing. We cannot assess ReproZip capture, replay correctness, or failure classification in this environment.

`reprozip pack` returned 0 after the failed first trace, but its config contains **no runs**. The generated `finite-difference.rpz` is an unusable diagnostic artifact, **not a successful experiment package**. No `reprounzip` execution attempted because there is no successfully captured run. Do not distribute that artifact as a replay.

## Conclusions and boundaries

- DVC successfully demonstrated the basic execution, dependency tracking, cache, metrics and error-handling capabilities we must retain/integrate with.
- ReproZip tracing/replay remains **not tested due to ptrace denial**, not an experimental loss against Paper Replay Lab.
- No speed rankings: one tiny CPU-only experiment is insufficient and instrumented command elapsed time mixes startup/cache/process overhead.
- No paper-level scientific result was validated. The specimen is an original numerical convergence demonstration with no third-party data.
- No advantage claim is supported yet. Next fair test: run the same explicit numerical checker inside a DVC stage and compare workflow/usability; run ReproZip on a permitted Linux host and actually unpack/re-execute its captured package.

## Additional real-paper aggregation baseline

DVC also ran the exact same pinned SpecEval adapter, upstream script and four released CSVs (stage dependencies: adapter and upstream directory). The 16 computed metrics exactly matched Paper Replay's clean-run metrics. Changing one HBN variance ratio caused the upstream numerical assertion to fail, and DVC correctly reported failure (exit 255 with underlying Python exit 1). Restoring the original data and forcing a rerun succeeded.

This demonstrates that DVC **can enforce the scientific numeric assertion when the stage includes it**. Paper Replay does not provide unique failure detection here. Its proposed additional value remains a standardized claim contract and portable consistency receipt. The sanitized command records and stdout/stderr remain outside this source distribution.
