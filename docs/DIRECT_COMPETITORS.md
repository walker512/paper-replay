# Private direct-competitor comparison, 2026-11-17

Author: walker512. Review status: independent audit completed; no publication or outreach.

## Question and common specimen

Does Paper Replay have a demonstrated advantage in checking all declared numeric claims and retaining inspectable evidence? The specimen is the same SpecEval paper (arXiv:2609.28560v1 Table 1), exact official released result CSVs at commit `4233473c92d0541e3f1a03d9b853f7bd1501152c`, 16 paper-displayed values and 0.05 percentage-point tolerance. This is result reaggregation, not new model generation or independent validation of the paper.

Fixed versions:
- Paper Replay Lab 0.1.2, `caf6ce172433afaebb57e37d4dc228db74499407`.
- VeriRepro 0.8.3, `f38d804a2e93d4f750932b702e287bd69132a7b6`, Apache-2.0.
- FullFighting/reproduce-research-paper 1.4.0, `33f0d330f64981826fc9ed20012e5f743be8918a`, MIT.

## Results, with execution scope kept distinct

| Deliberate input condition | Paper Replay installed import CLI | VeriRepro deterministic verification component | FullFighting deterministic runtime + report verifier |
|---|---|---|---|
| All 16 correct | 16 supported | PASS, 16 available comparisons | 16 reproduced within tolerance |
| `b8.oracle_pct` increased by 1 | 1 not_supported | FAIL, 1 mismatch | 1 NOT_REPRODUCED, 15 reproduced |
| Same key absent | 1 insufficient_evidence, 15 supported | PASS, 15 available comparisons | 1 BLOCKED, 15 reproduced |
| Entire metrics object empty | 16 insufficient_evidence | PARTIAL, zero comparisons | 16 BLOCKED |
| Metrics file absent | controlled CLI error, no receipt | not tested as required-file contract | 16 BLOCKED |

These are not end-to-end throughput rankings. Paper Replay imports already computed values without execution. FullFighting actually executed a reviewed transparent wrapper around the unchanged SpecEval aggregator. VeriRepro's component was invoked with host-authorized targets and an explicitly modeled successful prior execution; its full pipeline was not executed.

The wrong/missing mutation is deliberately applied after a successful scientific aggregation, testing the comparison layer rather than simply causing the author's built-in assertion to fail. FullFighting required a transparent flat-key-to-nested-JSON shape adapter; numeric data and targets were unchanged. Paper Replay's direct evaluator and installed import CLI agreed on the common scalar cases.

## What the differences mean

VeriRepro skips missing scalar values in its comparison list and documents PASS over the available authorized comparisons. Under an **all 16 required** contract, Paper Replay reports incompleteness more explicitly in this component test. This is a narrow, reproducible completeness-semantics difference. It is not a general assertion that VeriRepro's full pipeline falsely certifies papers; required artifacts and other gates were outside this comparison.

FullFighting correctly blocks the same missing claim and detects the same numerical mismatch. Its valid negative-outcome bundles pass integrity verification, which does not mean their claims pass. A one-byte tracked-artifact modification was rejected. Explicit claim contracts and portable re-checkable evidence are therefore **already demonstrated in a direct competitor**, not novel to Paper Replay.

## Whole-pipeline limitations

VeriRepro was installed and its real doctor/plan/no-execute CLI invoked. The actual paper-resolution stage could not resolve arxiv.org; Docker is also absent. This is an execution-environment limitation, not a competitive failure. Paper acquisition, model-assisted analysis, container execution, broad artifact comparisons and full end-to-end scientific outcomes remain unverified here.

FullFighting was tested without an LLM using its documented deterministic scripts. Its optional Codex planning, other data extractors, container controls, broad benchmark suite and non-Linux behavior were not independently validated. These are unknowns, not losses.

## Cost

All tests made zero model/API calls; no external agent was contacted. Only CPU, local files, package downloads and the attempted public paper resolution were used. Installation/setup labor, host compute charges, cloud storage and network costs were not measured. Per-command durations are preserved but do not support speed or cost rankings because scopes differ and one pipeline was blocked before execution.

## Decision supported now

No overall superiority is established. The strongest current product claim is a bounded one: Paper Replay provides a read-only existing-metrics import path with explicit unexecuted evidence labeling and all-declared-claims completeness semantics. Whether that interaction is easier or safer than the competitors' supported workflows still needs a matched usability/negative-case study. Do not claim competitors lack such an interface merely because it was not used in this run.

Avoid expanding features to manufacture a benchmark win. Compare the same user task with honest adapters and use the results to decide whether to keep this as a companion/import layer, integrate with existing projects, or pursue a different differentiated use case.

## Evidence and independent review

Raw local experiment logs remain private and are not included in this repository. A separate reviewer reran VeriRepro component cases, matched the 16 targets/tolerances and numerical payloads across tools, reverified all five FullFighting bundles, reproduced artifact-tamper rejection, and reverified four Paper Replay import bundles. Outcomes matched this report. This document is a reviewed summary, not a self-contained competitor benchmark distribution.

Sources: [VeriRepro](https://github.com/XiantingWu/VeriRepro), [FullFighting](https://github.com/FullFighting/reproduce-research-paper), [SpecEval](https://github.com/ShenQianli/SpecEval), [paper](https://arxiv.org/html/2609.28560v1). Fixed commits above define the tested versions. No external agent or upstream maintainer was contacted.
