# Value assessment after real competitor and sample tests

## Implemented, measured scope

- Read-only direct/DVC-exported JSON import now exists. It preserves exact source bytes, explicitly labels unexecuted evidence and reports all required missing claims. No original pipeline execution or authenticity is implied.
- A six-case original CMA-ES synthetic method experiment was genuinely run locally. The separate scalar checker checks saved arithmetic and budget consistency, not authentic execution. This is not external paper-table replication or evidence of general optimizer performance.
- Installed offline verification and imported-evidence handling passed private Ubuntu/Windows/macOS Python 3.11/3.12 CI. The CMA CI path only checks saved fixtures and imports results, not fresh optimization.
- Explicit `verify --require-supported` now provides a receiver CI acceptance gate without treating integrity-only success as claim success. Default behavior remains compatible; local positive/negative/missing/tampered/execution-failure CLI tests exercise the distinction. The final frozen receiver gate passed independent review and historical six-matrix CI; see VALIDATION.md.

## Competitive result, including unfavorable evidence

[Direct competitor study](DIRECT_COMPETITORS.md): FullFighting already checks explicit claims, blocks missing claims and detects changed evidence in the matched specimen. VeriRepro's tested component reports PASS over available comparisons, a narrower coverage meaning than our all-declared-claims status; its full pipeline was not evaluated. DVC with an author checker also correctly rejected bad results. ReproZip replay remains unknown due to host restrictions.

**No overall superiority, novelty monopoly, speed gain or cost gain is demonstrated.** Gate ergonomics and dependency-free receipt inspection are candidate conveniences, not proved competitive wins. No real users, adoption statistics, star growth or blinded human task-time measurements have been collected.

## Best next decision, not a feature backlog

Position provisionally as a claim/receipt companion to existing pipelines, not a replacement reproducibility platform. The important unresolved question is whether another researcher can hand off and interpret it with less effort or fewer mistakes than DVC plus a checker or FullFighting.

A real trial should use the same declared task and correct, numeric-failure, missing and tampered cases; counterbalance presentation order; record classification accuracy, setup steps and time. Predeclare that speed cannot trade off accuracy. Give users identical evidence and meaningful competitor instructions. Agent rehearsal can test instructions but cannot count as independent human adoption or an unbiased user study. Recruiting/contacting people is not authorized by this private implementation task.

Do not add a dashboard, agents, automatic paper discovery or statistical green checks to compensate for missing demand evidence. Present only the implemented companion workflow and these limits; publication is not evidence of user demand. A better outcome may be contributing an integration to an existing project rather than maintaining another broad framework; no external contribution or contact has occurred.
