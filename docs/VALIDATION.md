# Validation scope

## Current source candidate

The runtime, tests and scientific sample bytes are unchanged from private remote `320f53d81aa5c526e94ac741c24a927679646d2e` (local freeze `44182db78e8fea62cdefab608a68e161eedfa4cd`). Publication packaging updates documentation and workflow naming and excludes historical `evidence/` logs/receipts. The included samples/tests remain executable. A fresh extracted candidate is locally tested and installed into a new virtual environment before handoff; this is distinct from historical CI.

## Historical verification

Private CI run `44035855263` passed Ubuntu/Windows/macOS × Python 3.11/3.12. Linux/macOS each executed 74 tests; Windows executed 72 plus two POSIX-only skips. The eight receiver-gate tests ran on every matrix job. Original independent review approved the frozen version. During packaging recovery, the exact source ZIP was recovered and all 90 original file hashes were checked against that ZIP; the Windows 3.12 log was directly re-read. Other matrix results here are retained historical reports, not a claim that all logs were freshly recovered.

Earlier cross-platform receipts were downloaded and verified during development. They have not all been re-downloaded or reverified during this packaging pass. No GUI/browser acceptance is claimed: this is a CLI with Markdown reports, not a browser application.

Security regressions cover boolean/numeric distinctions, finite JSON numbers, bounded nesting, special-file/FIFO refusal, surrogate serialization, pinned input/artifact identities, explicit execution opt-in, negative/missing results and strict receiver gates. It is still not an execution sandbox, authenticated provenance system or scientific-truth checker.

## Scientific and competitor boundaries

- Finite difference: original synthetic numerical example; no external paper replicated.
- SpecEval: official pinned code aggregates released numerical CSVs and checks 16 displayed cells. No fresh LLM generation, independent observations or full paper experiment replication.
- CMA: six original synthetic optimizer trials were actually run and independently repeated in a pinned Linux CPython 3.12 environment during development. Included saved results and scalar-checker tests are not a new optimizer run or cross-platform optimization evidence.
- DVC with the author's checker rejected incorrect numerical output. FullFighting correctly handled missing/negative claims and changed evidence in the bounded matched study.
- VeriRepro's tested comparison component has different missing-value coverage semantics; its full pipeline was not evaluated. ReproZip capture/replay was blocked by host ptrace restrictions, not shown to be inferior.

No real-user timing/adoption study, growth guarantee, overall superiority, environment reconstruction guarantee or authentication of unsigned evidence is established. Private raw comparison logs are excluded; the reviewed comparison summaries preserve limits and adverse results.


## Runner lifecycle correction (new local candidate)

85 Linux/Python 3.12 tests pass, zero skipped (74 existing unchanged + 11 new).
Real processes exercise per-stream log ceilings, timeout, POSIX group cleanup
and SIGTERM cancellation. Controlled injections cover spawn-window SIGINT,
cleanup-phase deferred signals and postprocessing propagation. An offline wheel
install runs the original finite-difference example and integrity gate outside
the source checkout. This is not new Windows/macOS/hosted CI evidence and does
not certify arbitrary untrusted scripts, detached descendants, hard-kill cleanup,
transient disk bounds or real paper replication. README explains lifecycle and
partial-artifact limitations. No CI workflow is included in this change.
