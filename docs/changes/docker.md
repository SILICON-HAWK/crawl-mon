# Docker deployment slice

Added a minimal Python 3.12 slim CLI image running as non-root, an ignore file, and a Compose setup for PostgreSQL 17 plus one-shot CLI invocations. Compose defines persistent database and app data volumes, DB readiness ordering, no published DB port, configurable local credentials, and build/runtime CA secret wiring. Added usage and operational notes in `docs/docker.md`.

Files: `Dockerfile`, `.dockerignore`, `compose.yaml`, `docs/docker.md`.

Checks: not run by this task. Container build and Compose validation are handled by the coordinator with Docker daemon access.

Limitations: CLI only; no HTTP service or browser image. Compose uses local development credentials and no published database port. Runtime and test targets share installed dependencies; fixtures are only in the test target. Named volumes persist across container recreation.

Coordinator verification (2026-10-30): runtime and test images built successfully. All eight real PostgreSQL tests passed via `docker compose run --rm test discover -s tests -p test_postgres.py -v`. Runtime smoke checks passed for database listing, filesystem listing, and non-root UID 10001. PostgreSQL Compose health check passed.

Full Docker verification: `docker compose run --rm test` ran 121 tests in 51.873s with no skips: 115 passing test methods, six known regression methods failing (40 subtest/assertion failures and two lock errors). No new integration failures.
