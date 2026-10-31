# Per-user job actions

Added local JSON persistence and API endpoints for marking jobs interested or not interested. `GET /api/profile/{username}/job-actions` returns a mapping keyed by the exact job URL. `PUT` accepts `{ "job_url": "https://…", "status": "interested" | "not_interested" | "unset" }` and returns the full updated mapping; `unset` removes the URL. Decisions are stored in `user-assets/{username}/job-actions.json` separately from profile files.

The store validates safe usernames and HTTP(S) URLs without credentials, serializes updates with a per-user file lock, and replaces JSON atomically. Unknown users start with an empty map.

Affected files: `backend/src/jevscout/application/job_actions.py`, `backend/src/jevscout/interfaces/api.py`, and `backend/tests/api/test_job_actions.py`.

Checks: `.venv/bin/python -m unittest backend/tests/api/test_job_actions.py` passed (3 tests); `.venv/bin/python -m unittest discover -s backend/tests/api` passed (15 tests).

Limitations: file locking uses `fcntl`, so the storage adapter targets the local Unix environments used by this application. No outstanding work in this slice.
