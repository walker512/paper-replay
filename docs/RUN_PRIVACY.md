# New local run output permissions

`run --allow-execute` now creates its new output directory and missing parents
with POSIX mode 0700. Tool-written manifest, logs, receipt and Markdown members
are created exclusively with mode 0600, not opened by truncating an existing
name. The output leaf is not resolved through a symlink: both dangling and live
output links are rejected. Existing outputs are never reused or chmodded.

On POSIX the experiment subprocess starts with umask 077. This normally makes
its newly created metrics private without precreating the metrics pathname or
changing the parent process umask. Reviewed scripts still control their own
files: a script can deliberately change its umask/permissions, replace paths,
write elsewhere, or disclose data. This is not a sandbox or a guarantee about
arbitrary script-created artifacts. Windows inherits filesystem ACLs; these
mode bits are not a verified owner-only Windows ACL policy. No native Windows
run has been performed for this correction.

Use trusted stable ancestor directories and trusted scripts. POSIX tool writes
are directory-descriptor anchored and check the output identity between stages;
this does not isolate a hostile process running as the same user. Ancestor
symlinks and concurrent ancestor substitution are not comprehensively prevented.
A simultaneous creator of the output (or a missing parent) causes a safe failure,
not a merge. Existing member files and symlinks are not overwritten.

The bundle is **not transactional**. Errors, cancellation, process termination,
or power loss can leave a private partial directory. Nothing is recursively
removed and retries require a fresh output path. A partial directory is not a
successful receipt. Existing verification behavior and old bundle permissions
are unchanged; verifying an old 0755/0644 bundle does not tighten it.

Existing execution cleanup remains best effort: POSIX kills the original process
group, but descendants that escape it can survive. On Windows only the direct
child is killed/reaped, not a Job Object managed process tree. SIGKILL and power
loss cannot run Python cleanup. Receipts remain checks of declared computations,
not proof of scientific validity or trust in executed code.

The current Linux suite executes 117 public tests with no skips, including a
real subprocess under umask 022, three simultaneous CLI runs, legacy bundle
verification, link/member replacement and injected write failure. Existing real
signal/timeout/log-limit tests still run; this is not new remote CI evidence.
