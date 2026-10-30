# Subsystem test organization

Moved all existing tests into core, crawler, CLI, filesystem storage, database,
feeds, scoring, and utility packages. Shared fixture-site support lives under
`tests/support`; input fixtures stay under `tests/fixtures`. Model tests were
separated from filesystem storage tests. Imports and fixture roots now work with
recursive unittest discovery and subsystem selection using `-t .`.

Added Docker runtime coverage for non-root execution, installed dependencies,
and writable volume-backed CLI storage. Docker's test target enables that check.
`tests/README.md` documents suite boundaries, commands, and skip requirements.
No application behavior changed. Existing 123 tests were preserved; total is 124.

Read-only delegated coverage review confirmed current tests exercise crawler
limits, external redirects, SSRF protection, robots denial, retries, cancellation,
CLI lifecycle, extraction/scoring, and both persistence backends. Live source/API
compatibility remains outside these controlled tests.

Local check: `PYTHONPATH=src python3 -m unittest discover -s tests -t . -q`
passed with 26 dependency/environment skips. Full Docker check is recorded below.

Docker verification: `docker compose run --rm test` passed all 124 tests in 63.646s with no skips.
