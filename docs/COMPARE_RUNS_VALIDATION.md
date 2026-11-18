# Offline comparison increment validation

Baseline: public `0d1c109a899366a19f5da73b7a666e086d788b04` (56 files),
matched against the saved anonymous source archive. No CI workflow changes.

Linux / Python 3.12: 103 tests passed, zero skips (85 existing + 18 new).
New cases include actual execution versus imported snapshots, changed input/script
hashes, missing/null/boolean metrics, widened tolerances and removed claims,
failed execution metrics withheld, import-selection changes, deterministic output,
complete member tampering, malformed receipt CLI errors, symlinks/FIFO, bounds,
eight concurrent creators, exclusive member injection and partial write failure.
The installed offline-built wheel in a fresh virtual environment ran import-metrics,
compare-runs and compare-verify from outside the source directory successfully.

No new Windows/macOS, browser, hosted CI, real research replication or production
load test. POSIX-only mode/FIFO tests may skip on other systems. Windows ACLs,
hostile same-account directory replacement, hard power loss and authentication
are not established. Neither status changes nor matching hashes establish a
scientific improvement. Independent review and publication are pending.

## Combined unpublished candidate

The reviewed comparison increment and import-metrics privacy patch were combined
from the identical public baseline above. Their changed code/test paths do not
overlap; no reviewed implementation was overwritten. README's import-permission
statement was updated to describe the combination rather than the earlier single
increment. No workflow file was accessed or changed for this merge.

Full combined Linux/Python 3.12 suite: 111 passed, zero skips (103 comparison
candidate tests plus eight import-privacy tests). An offline wheel installed in
a fresh virtual environment completed import-metrics twice, compare-runs, and
compare-verify outside the source directory. Under umask 000, all new import and
comparison directories/files had mode 0700/0600. Expected unsupported-claim
import exit 2 was distinguished from failure. No Windows ACL, new browser or
hosted CI claim is made. Combined independent review and publication are pending.
