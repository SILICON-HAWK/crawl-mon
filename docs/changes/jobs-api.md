# Aggregated jobs API

Added `GET /api/jobs` to return extracted jobs across saved runs, ordered by the run's `created_at` newest first. Each response item preserves the extracted job fields and adds `run_id`, `job_index`, and `originals` (an array of `{run_id, job_index}` references). A valid `application_url` is used for duplicate detection after normalizing scheme/host case, default ports, trailing slash, and fragment; the newest copy is returned while all source indices are retained. Jobs without a usable application URL remain separate. Stored evaluations are not attached because they can contain user-specific decision data.

## Files

- `backend/src/jevscout/interfaces/api.py`
- `backend/tests/api/test_jobs.py`

## Verification

- `PYTHONPATH=backend/src .venv/bin/python -m unittest discover -s backend/tests/api -v`

## Limitations

- Existing runs are read as stored; this endpoint does not re-extract old evidence.
- Deduplication is limited to equivalent normalized application URLs; query parameters remain significant.
