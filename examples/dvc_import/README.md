# Read-only import of existing DVC metrics

`dvc-export.json` is actual `dvc metrics show --json` output from the local DVC 3.67.1 baseline, not synthetic expected values. The experiment was the original MIT finite-difference script by walker512. See `docs/BASELINE_RESULTS.md` for how that prior experiment was executed. This example only reads the stored metrics; it does not rerun DVC or the experiment.

```sh
paper-replay import-metrics examples/dvc_import/contract.json --metrics examples/dvc_import/dvc-export.json --select "//data/metrics.json/data" --out imported-results
paper-replay verify imported-results
```

For an actual existing flat JSON metrics file in a DVC project, omit `--select`:

```sh
paper-replay import-metrics path/to/contract.json --metrics path/to/metrics.json --out imported-results
```

No DVC installation or scientific dependencies are required for import or verification. The original source file is copied byte-for-byte into a fresh evidence directory, so review it for private information before sharing. The original files are not edited, no project script is loaded, and no DVC command is invoked.

The selection string is an explicit object-key JSON Pointer. In this real DVC export, the top-level workspace key is the empty string, hence the initial double slash. File names or revision keys containing `/` use `~1`; literal `~` uses `~0`. Array indexing and auto-detection of DVC versions/revisions are deliberately unsupported. Selection must end at an object; individual claims refer to its flat metric keys.

A result of `supported` means the **imported numbers** meet the declared thresholds. It does not mean the DVC pipeline just ran, the data is fresh, the upstream run succeeded, or the measurements are authentic. We do not interpret upstream error/status metadata. The receipt explicitly sets `evidence_mode: imported` and `executed: false`; its verifier re-extracts the selected source object as well as checking the claims.
