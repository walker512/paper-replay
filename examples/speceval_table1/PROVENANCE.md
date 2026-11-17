# External paper example: SpecEval Table 1

## Source identity

- Paper: Qianli Shen et al., *Speculative Evaluation of Stochastic LLMs*, arXiv:2609.28560v1, Table 1.
- Paper source: https://arxiv.org/html/2609.28560v1
- Official code: https://github.com/ShenQianli/SpecEval
- Pinned commit: `4233473c92d0541e3f1a03d9b853f7bd1501152c`
- Files obtained 2026-11-17; SHA-256 values of executable code and result inputs are in `manifest.json`.

`upstream/tools/reproduce_table1.py` and the four `upstream/results/replay/*.csv` files are byte-for-byte copies from the above commit. The original MIT notice is retained in `upstream/LICENSE`. The CSVs contain the authors' published numerical per-profile measurements, not benchmark questions, answers, private examples, model weights or personal data. The upstream data source notice explicitly distinguishes these released statistics from third-party benchmark text. That text has NOT been downloaded or redistributed.

## Exact claim boundary

We run the authors' own aggregation function over their released results: 107 profiles × 4 budgets × 4 methods. All 16 table cells are compared to the paper's displayed one-decimal percentages, using 0.05 percentage-point absolute tolerance. This is a display-precision check, not a statistical confidence interval. The upstream function additionally enforces its exact one-decimal formatting check and complete profile/budget grids.

The adapter only converts upstream computed values to a flat JSON metric file. It does not substitute the paper's expected values for computed metrics. The benchmark is **published-result reaggregation**, not fresh Monte Carlo statistical replay, GPU inference, reconstruction of original rollouts or independent validation of the scientific conclusions. The fixed input measurements are accepted as inputs, not verified observations.

The upstream already validates all 16 displayed values itself. We do not claim the same checks are novel or stronger. Paper Replay adds an explicit claim manifest, hash checks and an offline re-checkable receipt around that workflow.

## Clean run

A newly created Python 3.12 venv, with no inherited site packages, installed Paper Replay Lab from its local source. The installed CLI was run from `/tmp`, outside the checkout. The example required only the standard library. All 16 claims passed and offline receipt verification returned `consistent`.

Representative HBN values (% of Uniform variance): b=8: 87.24758406997087; b=16: 80.12329704507785; b=32: 73.02991822676867; b=64: 66.43681905074959. The sample can regenerate exact results into the output directory you choose; historical run receipts are not bundled.

## Audit limits

No benchmark access agreement was accepted; no paid model call or user credential was used. The paper itself is linked, not republished; arXiv's paper license is not assumed to be MIT. This distribution includes only that selected released-code/numerical-result subset, with the original MIT notice and attribution. It does not redistribute benchmark questions, prompts, answers, paper text or model weights.

Fixed-revision source/redistribution boundary: https://github.com/ShenQianli/SpecEval/blob/4233473c92d0541e3f1a03d9b853f7bd1501152c/data/SOURCES.md

The initial Git working-tree copy converted the four CSVs to CRLF according to upstream attributes. Independent review detected that byte-level discrepancy. The retained files were replaced with exact `git show <commit>:<path>` blob bytes (LF), the manifest hashes updated, and the clean installed-CLI experiment and all tests rerun. Numerical values were not changed.
