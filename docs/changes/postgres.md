# PostgreSQL storage adapter

Added `PostgresRunStore(dsn, root)` as a PostgreSQL implementation of the filesystem store's public persistence methods. PostgreSQL holds run records, page metadata and HTML artifacts, execution documents, results, and evaluations. The `root` directory is used only for per-run engine workspaces. Call `initialize_schema()` explicitly; it is safe to repeat for schema version 1. Psycopg 3 is an optional runtime dependency, supplied by packaging outside this task.

The adapter validates canonical run IDs and page artifact references, uses parameterized SQL, commits each page and its metadata in one transaction, and gives each store instance a reentrant PostgreSQL advisory lock shared across the database regardless of workspace path. Database connection/operation failures are exposed as generic errors without including the DSN.

Files changed: `src/jevscout/postgres.py`, `tests/test_postgres.py`, and this note.

Checks: `PYTHONPATH=src python3 -m unittest tests.test_postgres -v` discovered eight integration tests; all eight were skipped because `JEVSCOUT_TEST_DATABASE_URL` is unset. `python3 -m py_compile src/jevscout/postgres.py tests/test_postgres.py` and `git diff --check` passed. The integration tests require that variable to point at a disposable PostgreSQL database and use real connections; this environment did not run the database assertions. This first schema has no migration framework or filesystem-data import. Call `initialize_schema()` (or CLI `db init`) before storage operations. Advisory locking is database-wide for this adapter, so different containers and engine workspace roots contend on the same lock.

Coordinator verification (2026-10-30): runtime and test images built successfully. All eight real PostgreSQL tests passed via `docker compose run --rm test discover -s tests -p test_postgres.py -v`. Runtime smoke checks passed for database listing, filesystem listing, and non-root UID 10001. PostgreSQL Compose health check passed.

Full Docker verification: `docker compose run --rm test` ran 121 tests in 51.873s with no skips: 115 passing test methods, six known regression methods failing (40 subtest/assertion failures and two lock errors). No new integration failures.
