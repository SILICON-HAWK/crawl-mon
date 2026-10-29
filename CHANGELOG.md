# Changelog

Record user-visible behavior, verification, and limitations for each usable slice. Dates are UTC. Agent contribution notes live in `docs/changes/`; the coordinator reviews and incorporates them here before committing. Do not record credentials or private source/profile data.

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
