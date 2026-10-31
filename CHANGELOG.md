# Changelog

Record user-visible behavior, verification, and limitations for each usable slice. Dates are UTC. Agent contribution notes live in `docs/changes/`; the coordinator reviews and incorporates them here before committing. Do not record credentials or private source/profile data.

## Subsystem test organization — 2026-10-30

- Grouped tests into core, crawler, CLI, filesystem storage, database, feeds, scoring, utilities, and Docker packages; centralized shared fixture support.
- Preserved all existing tests and added a non-root Docker packaging smoke check. Updated discovery commands and test documentation.
- Full Docker suite: 124 tests passed, no skips (63.646s). No application logic changed.

## Regression stabilization — 2026-10-30

Validation: rebuilt app/test images; `docker compose run --rm test` passed all 123 tests in 50.846s with no skips, including live PostgreSQL, crawler fixture, CLI, and regression checks.

- Fixed automatic extraction during scoring to hold one storage lock while retaining terminal-run validation and execution-report updates.
- India filtering distinguishes the country name and standalone uppercase country code from English prose and US state abbreviations.
- Evaluation IDs now retain application URLs when explicit IDs and legacy URL fields are absent; duplicate titles no longer collapse distinct posting identities.
- Coordinator reviewed failures as logic defects; no failing expectations were weakened. Added guard/report and standalone-country-code controls, and retained the earlier regression tests.

## Docker and initial PostgreSQL storage — 2026-10-30

- Added non-root Python CLI runtime and test images, Compose PostgreSQL 17 service, persistent volumes, readiness checks, and build/runtime CA mounting. See `docs/docker.md`.
- Added optional `postgres` dependency and a PostgreSQL adapter storing runs, evidence, execution reports, results, and evaluations. Database-wide advisory locking coordinates synchronous operations across workspace roots; nested operations on one store are supported.
- CLI selects PostgreSQL using `JEVSCOUT_DATABASE_URL`; `db init` explicitly initializes schema version 1. `JEVSCOUT_DATA_DIR` configures filesystem data or engine workspaces. Filesystem remains the default.
- Verified image builds, eight real PostgreSQL integration tests, CLI round trips, non-root UID, filesystem smoke check, and database health. The pre-existing intentionally failing regression tests remain unchanged.
- No background queue, filesystem import, crash-resume guarantee, or external publication is included.

## Saved decision reuse — 2026-10-31

- Reuse saved per-user job decisions, including duplicate postings in other runs, before calling OpenRouter; serialize identical requests across API processes. Show a clear error for provider rate limits and keep saved decisions available.
- Added the default-on AI insights display toggle. The free-model batch stopped after the provider reported its daily limit. Saved decisions do not automatically refresh when a profile changes.

## Technical job selection — 2026-10-31

- Default Jobs view and new pipeline ranking select technical titles while excluding sales, teaching and recruiting; raw collected feed records remain available for review. The conservative title filter can miss relevant unconventional titles.
- Restarted the decision batch against the filtered jobs; existing evaluations were reused.

## Landing page spacing — 2026-10-31

- Put the Explore jobs action on its own row with consistent spacing across screen widths.

## Landing page — 2026-10-31

- Restored the welcome introduction on Home only; Jobs, Runs and Profile remain focused views.

## Job review modes and buckets — 2026-10-31

- Replaced the long jobs list with one-at-a-time Reels and swipe-card views; removed the landing-page hero.
- Added per-profile Interested and Not interested buckets, reversible without deleting jobs. Decisions persist as local JSON with cross-process locking.
- Tested API behavior and staged the built frontend before switching the stable port.

## Separate jobs pages — 2026-10-31

- Added distinct Jobs, Runs and Profile URLs with browser navigation; job descriptions stay hidden until expanded. Existing decision results are shown on matching jobs, including duplicate source runs. Improved mobile readability.
- Staged and checked a separate built frontend snapshot before switching the stable service.

## Profile and job connection checks — 2026-10-31

- Classification now reports missing profiles and missing saved jobs separately, with a recovery action for each. Confirmed both running interfaces resolve the same saved profile and all 748 visible jobs point to existing results.

## Jobs browser and built app — 2026-10-31

- Added separate Jobs, Runs and Profile views; Jobs combines saved results with card/list views, application links, requirements excerpts and explicitly disclosed salaries.
- Retain salary data from feed and JSON-LD sources where provided. Re-extracted saved feed evidence: 748 unique jobs, 85 with salary.
- Added built frontend snapshot served with the API separately from the Vite dev server. Both use the same filesystem data; pipeline status is process-local.

## Local profiles and decision analysis — 2026-10-31

- Added per-user private JSON profiles and file directories, editable profile UI, responsive card/list views, and per-job decision-model analysis with separate dimensions and persisted results.
- The free OpenRouter Respan model receives the saved profile and selected job only when the user clicks Analyze; its probabilities are experimental.
- Bounded live feed retry extracted 748 records across four sources; one feed dominated and source normalization needs review. See `docs/changes/background-collection.md`.

## Local dashboard and bounded pipeline — 2026-10-31

- Added Svelte/Vite dashboard and local FastAPI interface to inspect runs and start and monitor bounded feed collection and offline heuristic ranking.
- Pipeline accepts up to five explicit seeds, runs one at a time, and preserves source/run provenance. Status and rankings are in memory; saved runs and evidence persist.
- Added a full data-flow plan and local setup instructions. No résumé is loaded automatically and no remote model is called.
- Verified API-to-pipeline-to-storage integration with a controlled fixture, a real Ashby feed (13 extracted jobs), and frontend production build.

## Backend package organization — 2026-10-31

- Grouped Python code into core, application, jobs, adapters, storage, and interface packages; updated imports and the CLI entry point.
- Existing Python import paths changed; command-line behavior remains the same. Docker and PostgreSQL integration verification is deferred.

## Repository layout — 2026-10-31

- Moved the Python package and tests into `backend/`, container files into `deploy/`, and reserved `frontend/` for a future UI.
- Updated package setup, container build paths, and main usage instructions. Internal Python module organization remains upcoming.

## Agnostic decision scoring engine & OpenRouter integration — 2026-10-29

- Added provider-agnostic decision scoring module (`src/jevscout/scoring/`) supporting OpenRouter Decisions API (`POST https://openrouter.ai/api/alpha/decisions`).
- Default model configured to free decision model `respan/span-01-lite:free` with full support for `typesafe/jev-1.13` and other decision models via `--model`.
- Added typed decision primitives (`NoulAnswer`, `ChoiceAnswer`, `ScoreAnswer`), `CandidateProfile`, and `JobMatchEvaluation`.
- Implemented match rubrics (`rubrics.py`) for location compatibility (`noul`), seniority fit (`choice`), and tech stack alignment (`score`).
- Added composite scoring engine (`engine.py`) computing normalized 0–100 match ratings with categorical recommendation tiers (`STRONG_MATCH`, `REVIEW`, `PASS`).
- Added `LocalHeuristicDecisionClient` for 100% offline development, testing, and deterministic evaluation without requiring external keys or network.
- Added storage persistence for match evaluations (`save_evaluations`, `list_evaluations`) in `FileRunStore`.
- Added CLI subcommands `runs score` and `runs evaluations` with `--offline`, `--role`, `--skills`, `--locations`, `--remote-only`, and `--profile-json` flags.
- Added end-to-end integration test from career feed scraping through India extraction to decision model scoring.

Verification: 104 passing tests across full suite (`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests`). Agent note: `docs/changes/decision-scoring.md`. Zero network required during automated tests.


## Complete 6-provider ATS feeds, token harvesting and quality guards — 2026-10-29

- Added browserless public feed adapters for all 6 verified ATS platforms: Greenhouse, Lever, Ashby, Breezy HR, Recruitee, and Teamtailor.
- Added Common Crawl CDX token harvester (`harvester.py`) for discovering public company tokens via SURT key extraction and building unauthenticated API endpoints.
- Added quality guards (`quality.py`): CDN URL and script boilerplate sanitization, technical role title scoping for ambiguous industry acronyms (`dbt`, `PHP`), and department explosion mitigation (>25 threshold).
- Enforced strict India-only location filtering (`is_india_eligible`, `normalize_india_location`) across all 6 providers with canonical tech hubs and India-eligible remote roles.
- Diagnostic logs updated across all feed adapters to maintain strict privacy without leaking source URLs in debug output.

Verification: 90 passing tests across unit, integration, and CLI suites (`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`). Agent notes: `career-feeds.md`, `all-ats-feeds.md`. No third-party network or paid APIs used.



## Collection foundations — 2026-10-29

- Added pure JSON-LD JobPosting extraction from saved HTML, including arrays and `@graph`, explicit unknown fields, HTML description cleanup, and source/artifact provenance.
- Added versioned result sets, execution reports, run-isolated engine workspaces, and a nonblocking local operation lock. Replaced neither the application queue nor distributed coordination with files.
- Added an explicit persisted `allow_local` flag for loopback fixture collection; existing run documents default it to false.
- Defined the framework-independent collection interface. Real Crawlee execution/CLI integration is in progress and is not part of this foundation checkpoint.

Verification: 13 storage, 4 CLI-regression, 4 result-storage, 2 parser, and 2 scope checks pass (25 checks across targeted commands). Agent notes: `job-extraction.md`, `result-storage.md`. No live sources or JEV calls used.

## 0.1.0 — Filesystem run requests — 2026-10-29

- Added a Python package and CLI for creating, listing, and inspecting pending run requests with JSON output. No runtime dependencies or database server are required.
- Added validated seed/limit records, UUID-based run directories, atomic metadata/artifact replacement, and content-addressed page observations that preserve changed content and metadata.
- Reject credential-bearing URLs, malformed limits, unsafe identifiers/artifact references, and non-JSON page metadata. Report malformed stored run records without a traceback or leaked contents.
- Added redacted diagnostic logs, usage/setup instructions, and ignored runtime/build artifacts.
- Integrated scoped Luna contributions and independent review. Review fixes preserve observation history and reject credential-bearing artifact URLs; CLI corruption errors are handled safely.
- Refreshed the project-root handoff and retained implementing-agent notes in `docs/changes/`.

Verification: `PYTHONPATH=src python3 -m unittest discover -s tests -v` passes 17 tests. Editable package installation succeeded in the local `.venv`; installed CLI create/show passed across separate processes. Documentation links/code fences and Git whitespace checks passed.

Limits: one trusted local writer, no application queue, no background execution, no crawling/extraction/JEV yet. Atomic individual-file replacement is not a multi-file transaction or power-loss durability guarantee. Crawlee collection is the next slice; PostgreSQL is deferred.

## Architecture planning checkpoint — 2026-10-29

### Architecture and execution

- Selected filesystem persistence for the first low-resource implementation. PostgreSQL is the intended later backend, not a required local service.
- Start with a single local process and synchronous operations. Shared application queues, distributed claiming, background execution, and multi-container recovery are deferred; do not approximate them with an untested file queue.
- Keep storage behind a small adapter boundary. Crawlee remains the selected crawling engine; no crawling or classification is implemented in this planning checkpoint.
- Added the phased execution plan and clarified that database-first steps are superseded by the filesystem-first slice.

Verification: documentation whitespace checks. No application checks at this checkpoint.

Full Docker verification: `docker compose run --rm test` ran 121 tests in 51.873s with no skips: 115 passing test methods, six known regression methods failing (40 subtest/assertion failures and two lock errors). No new integration failures.
