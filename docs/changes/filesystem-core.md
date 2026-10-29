# Filesystem persistence core

`RunSpec` validates seed URLs and bounded collection limits, and supports strict
dictionary serialization. `RunRecord` stores the run ID, specification,
status, UTC creation time, and optional error. `FileRunStore` persists run JSON
and per-page HTML plus metadata under the configured root. Run metadata uses
atomic replacement. IDs are generated locally as UUIDs; run IDs and artifact
references are checked before paths are formed. Page names use the SHA-256 of
the original URL, HTML content, and canonical JSON metadata separated by NUL
bytes, while metadata preserves the URL unchanged. Re-saving identical
URL/content/metadata reuses the artifact; changed content or metadata preserves
the earlier observation. Saved page URLs are validated as HTTP(S) URLs, and
metadata must be JSON serializable before any artifact is written. HTML and
metadata writes use temporary files and atomic replacement; this does not
promise a power-loss transaction.

The public seams exercised are `RunSpec` construction/serialization and the
`FileRunStore` create, get, list, update, save-page, list-pages, and
read-artifact methods. No logs include run payloads or page content.

## TDD checks

Command used for each cycle:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_storage.py
```

- **RED, RunSpec seam:** the first run failed to import `jevscout.models`, as
  expected before the model was implemented.
- **GREEN, RunSpec seam:** after adding validation and serialization, the same
  command passed both RunSpec checks.
- **RED, persistence seam:** after adding the persistence test, the command
  failed to import `jevscout.storage`, as expected before the store existed.
- **GREEN, persistence seam:** after implementing the store, the command
  passed. The final run reports `Ran 6 tests ... OK`, covering invalid specs,
  cross-instance persistence and updates, page HTML/metadata round-trip with
  the original URL, and rejection of unsafe IDs and artifact references.
- **RED, regression seams:** adding malformed URL, status, mutable-spec, and
  changed-page-content cases produced 7 test failures, confirming those gaps.
- **GREEN, regression seams:** after validating parsed URL host/port data,
  snapshotting specs, restricting run statuses, and atomically storing
  content-addressed page artifacts, the command reports `Ran 10 tests ... OK`.
  The added checks cover malformed hosts/ports/IPv6, backslashes and control
  characters, uppercase schemes, status validation, snapshot persistence, and
  retention/idempotence for changed/identical page content.
- **RED, observation regressions:** the command then failed on two new public
  checks: changed metadata reused the same artifact reference, and a
  credential-bearing page URL was accepted.
- **GREEN, observation regressions:** including canonical metadata in the
  artifact identity, validating page URLs, and rejecting non-JSON metadata
  before writing artifacts brings the final command to `Ran 13 tests ... OK`.
  It verifies old/new metadata observations remain readable and invalid URLs
  or metadata leave the run's artifact list empty.

## Limits

This is a single-writer filesystem store for synchronous use. It does not
implement a job queue, crash resume/recovery, multi-writer coordination,
database-backed state, or concurrent write guarantees. Artifact retention and
deletion policy remain open.
