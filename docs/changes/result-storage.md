# Execution and result persistence

`FileRunStore` now reads and writes one execution JSON object per existing run and stores extracted items in a versioned results document (`schema_version: 1`, `parser_version: "jsonld-jobs-v1"`). Missing execution data reads as `None`; results default to an empty list. Writes require an existing run and reject non-object payloads, malformed item shapes, and non-JSON values including NaN before replacing prior data. `operation_lock()` holds a nonblocking exclusive `fcntl.flock` on a private `.operation.lock` file for the storage root and releases it when the context exits, including on exceptions. `engine_workspace(run_id)` validates the run and returns a created, run-specific `engine/` directory as a resolved path.

Files: `src/jevscout/storage.py`, `tests/test_result_storage.py`.

Checks performed:

- `PYTHONPATH=src python3 -m unittest discover -s tests -p test_result_storage.py` — 4 tests passed, including fresh-store round-trip, invalid-write preservation, missing-run rejection, per-run workspace isolation, and lock contention/reacquisition across processes.

Limitations: this is local application persistence and an advisory single-operation lock for Linux/WSL. It is not a queue, resume mechanism, crash recovery guarantee, or distributed/multi-writer coordination system. Platforms without `fcntl` report locking as unsupported; no live crawler or end-to-end pipeline behavior was exercised.
