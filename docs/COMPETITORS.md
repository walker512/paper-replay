# Competitors and distinct scope

Reviewed 2026-11-17. This is a documentation comparison, **not a performance benchmark**.

- ReproZip: https://docs.reprozip.org/en/latest/ captures OS calls and packages executable dependencies for reproduction. We do not implement that capability. Future adapter should preserve its environment packaging.
- DVC: https://doc.dvc.org/user-guide/experiment-management runs, tracks and compares code/data/parameters/metrics/plots and shares experiments. We do not outperform its experiment lifecycle support. Future adapter should consume DVC artifacts and preserve DVC tracking.

Our proposed additional workflow: explicitly link a research claim to a metric rule, pin the local experiment, and produce a status-bearing independently recomputable receipt. This is a hypothesis of usability value, not evidence competitors cannot implement it with a small script.

## Required real comparison

1. Freeze three legal public research examples with runnable code/data and author-specified or carefully justified claim thresholds.
2. Run manually, with DVC, with ReproZip, and with this claim layer plus those tools where appropriate. Record exact versions/configuration and failures, not just successes.
3. Introduce missing dependencies, changed data, wrong metric, nonzero exit and stale metrics. Score diagnosis correctness, setup effort, time to locate the mismatch, and false passes.
4. Separate environment recreation (where ReproZip is expected to help) from experiment tracking (DVC) and per-claim review (our proposed benefit).
5. Publish the reproduction commands and negative results. Do not choose only tests that favor this prototype.

The follow-up baseline installed DVC 3.67.1 and ReproZip 1.3.2 in an isolated venv. DVC passed both the original numerical workflow and the same real-paper aggregation plus negative-value test. ReproZip tracing was blocked by host ptrace restrictions, so capture/replay remains unverified. See [actual results](BASELINE_RESULTS.md). No comparative superiority is claimed.

## Portfolio separation

QueryProof concerns SQL result evidence. AI Cost Lab concerns model quality/cost. This prototype concerns user-authored scientific/computational claim acceptance. Agent Incident Lab concerns coding-agent failures. Evidence-format utilities may be shared later; these repositories were not modified.
