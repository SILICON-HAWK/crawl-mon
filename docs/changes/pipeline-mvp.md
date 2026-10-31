# Bounded pipeline MVP

`PipelineManager` provides explicit start, list, and get operations for a small
single-process pipeline. A start validates one to five HTTP(S) source URLs and
a candidate profile, then launches one background worker. The worker creates
ordinary application runs and executes them through `execute_run`, with five
pages, depth zero, and a 120 second timeout per source. It extracts the saved
jobs and ranks them locally from role, skill, and location overlap. Ranked
results include their source URL and run ID.

The manager permits one active pipeline at a time and exposes queued/running
and terminal state, per-source run status, and result provenance. The state is
held in process memory; worker updates and API snapshots share a lock, and run
evidence remains in the configured run store. Input checks reject malformed
seed values, blank profile terms, and non-finite or negative experience.
There is no automatic model call, restart recovery, or unbounded crawl.

Files: `backend/src/jevscout/application/pipeline.py`,
`backend/tests/core/test_pipeline.py`.

Check: `PYTHONPATH=backend/src python3 -m unittest backend.tests.core.test_pipeline`
Result: 2 tests passed.

Limitations: this MVP is single process and loses pipeline summaries on restart.
The API host must call `start` only for an explicit user request.
