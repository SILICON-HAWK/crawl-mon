# Stabilization fixes

Scoring now extracts saved evidence through a lock-aware internal path, so `score_run` holds one operation lock for the full scoring transaction while extraction keeps its terminal-run guard and updates the execution report. Scoring identity now falls back from explicit `id` to `url`, then `application_url`, then title. India filtering now requires an explicit India country name or a recognized Indian hub; English “in” and the US state abbreviation in Indianapolis no longer count as India evidence.

Affected files: `src/jevscout/application.py`, `src/jevscout/scoring/engine.py`, and `src/jevscout/feeds/location.py`.

Checks run:

- `PYTHONPATH=src:tests python3 -m unittest -v test_scoring_regressions test_location_filter` — 16 tests passed, including the standalone uppercase `IN` country code control.
- `PYTHONPATH=src:tests python3 -m unittest -v test_application test_cli test_extraction test_feed_integration test_ashby_feed test_breezy_feed test_greenhouse_feed test_lever_feed test_recruitee_feed test_teamtailor_feed` — 38 tests passed.

No known remaining work in this slice. Coordinator rebuilt both Docker images and ran `docker compose run --rm test`: all 123 tests passed in 50.846s, no skips, including live PostgreSQL. Live external provider compatibility was not exercised.
