# Receipt portability and byte identity

## Observed issue in 0.1.0

The private CI run [44026054956](https://github.com/walker512/paper-replay-lab/actions/runs/44026054956) tested Ubuntu/Windows/macOS on Python 3.11/3.12. All six passed 29 tests and the installed CLI example. All sixteen measured values matched across the six systems.

However, `Path.write_text()` used OS-default newline conversion for generated manifest copies. Windows copies were 5,780 bytes with 135 CRLF endings; Unix copies were 5,645 bytes with LF endings. The parsed JSON was equivalent, but hashes differed:

- Unix: `d6078b3114d99e10fe2af7a36642e60368f907df8a1606ff15280aa60eb8adf7`
- Windows: `20d34022d84f5575ff573bd527153d8958f6516fafdf7ce42f92a99a38e42e62`

This did NOT invalidate either bundle: each receipt correctly bound its actual bytes, and all six old bundles were verified locally using 0.1.1. It WAS a reproducibility/usability defect if users tried to identify the same manifest across platforms by the generated copy's digest.

## Fix in 0.1.1

Own JSON metadata now serializes with sorted keys, UTF-8 and literal LF, then writes bytes. Markdown reports also use UTF-8/LF bytes. No platform text conversion is involved. This is a deterministic application serialization, **not a claim to implement RFC 8785 JSON Canonicalization Scheme**. Numeric forms such as `1` and `1.0` remain distinct.

Raw script inputs, metrics and logs remain raw-byte-hashed. The verifier does NOT normalize line endings or disregard changed bytes. This preserves detection of accidental/malicious transport conversions. Transfer receipts as binary-preserving archives, not through a text editor. An unsigned, wholly replaced bundle can still be self-consistent; this fix adds no authentication.

Receipt schema 1 remains supported for tool versions 0.1.0 and 0.1.1. Legacy Windows CRLF bundles verify when their actual bytes match their receipt; converting them without updating the receipt correctly fails. An explicit regression covers this case.

Whole receipts are intentionally NOT byte-identical across runs: durations and self-reported Python/OS fields vary. Experiment metrics/logs are also not forced to match. Only the tool-generated manifest copy is expected to be stable for the same parsed manifest under the supported serialization.

## Verification state

- 32 local tests passed, including UTF-8/LF byte writes, stable key ordering, generated output encoding and legacy Windows/tamper behavior.
- Rebuilt 0.1.1 wheel installed in a clean venv; external-paper aggregation still 16/16 supported, receipt consistent.
- All six actual 0.1.0 CI bundles verified unchanged with the 0.1.1 verifier.
- **Historical note superseded:** 0.1.1 and the final 0.1.2 runtime subsequently passed their own six-platform CI. See VALIDATION.md; the original 0.1.0 result alone was not proof of later versions.
