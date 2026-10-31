# Current profile and analysis work

Profile data and files are ignored under `user-assets/<username>/`; the local API uses `JEVSCOUT_USER_ASSETS_DIR`. The abhi profile was initialized from local context; experience years was set to zero as an unknown placeholder and requires user correction. Per-job analysis uses the free OpenRouter Respan model after an explicit click and saves dimensional answers with the run. Results are experimental. See `docs/changes/background-collection.md` for live feeds and known source quality issues. User requested a separate full data-flow review, still pending.

# Dashboard MVP continuation

Local frontend, API, and bounded offline ranking pipeline are described in [frontend MVP](docs/frontend-mvp.md) and [plan](docs/frontend-mvp-plan.md). Stage-by-stage pipeline and decision-quality review remains a separate user-requested task. Pipeline state is in memory; it neither automatically reads the private résumé nor calls a decision model. Use TDD for future behavior changes and handoff for the next continuation. No remote push has been requested for this MVP.

# Current continuation

Local `main` includes `origin/codex/integration/docker` through `b837e4a`. The repository layout now uses `backend/`, `deploy/`, and `frontend/`. The backend package is organized by responsibility; see the README for the package map. Python import paths changed. Docker and PostgreSQL verification were deferred at the user’s request. Remote `main` has not been updated. The historical sections below include stale paths and status.

Latest test-layout verification: all 124 Docker tests passed with no skips (63.646s).

Tests are organized by subsystem under `tests/`; see `tests/README.md`. Use `PYTHONPATH=src python3 -m unittest discover -s tests -t . -v`, or select a subsystem folder. The Docker test target runs every dependency-backed suite plus a packaging smoke check. Earlier flat-file test commands below are historical.

Latest stabilization verification: all 123 Docker tests passed with no skips (50.846s), including live PostgreSQL and controlled-fixture collection. App/test images rebuilt. The earlier failing-suite counts below are historical. Live external provider compatibility was not exercised.

# Current integration update — 2026-10-30

Work is on `codex/integration/docker`, branched from `gemini/feature/job-portal`.
The user authorized Docker packaging and the first PostgreSQL integration, superseding the earlier postponement below. Filesystem storage remains available by default. Set `JEVSCOUT_DATABASE_URL` for PostgreSQL and explicitly run `jevscout db init`. See `docs/docker.md` for non-root runtime/test images and Compose commands. PostgreSQL holds metadata and page evidence; local storage holds engine workspaces. No filesystem import, worker queue, or crash-resume support is included.

The prior tests-only regressions are now fixed under the user’s stabilization request: filesystem scoring uses one operation lock, India filtering distinguishes country names/codes from prose and US state suffixes, and evaluation identities retain application URLs. `tests/test_postgres.py` requires a disposable database URL in `JEVSCOUT_TEST_DATABASE_URL`.

# JevScout handoff

## Workspace and repository

- Project and Git root: `/home/abhi/work/jevscout`. Run project commands here, not in `/home/abhi/work`.
- Repository: https://github.com/SILICON-HAWK/crawl-mon
- Active Branch: `gemini/feature/job-portal` (tracking `origin/gemini/feature/job-portal`).
- Latest verified state: Agnostic decision scoring engine (`src/jevscout/scoring/`) with OpenRouter Decisions API support (`respan/span-01-lite:free` and `typesafe/jev-1.13`), offline heuristic mode, candidate profile matching, composite scoring (0–100), and filesystem evaluations storage. 104 tests passing.

## Current task and stopping point

The decision scoring pipeline is fully complete and verified with an agnostic module name (`src/jevscout/scoring/`). It supports:
1. `OpenRouterDecisionClient` targeting `respan/span-01-lite:free` (free decision model) and `typesafe/jev-1.13` (paid/enterprise) via OpenRouter Decisions API (`POST /api/alpha/decisions`).
2. `LocalHeuristicDecisionClient` for zero-network, zero-credential local evaluation and testing.
3. Candidate profile modeling (`CandidateProfile`), typed rubrics builder (`rubrics.py`), and weighted composite scoring engine (`engine.py`) with recommendation tiers (`STRONG_MATCH`, `REVIEW`, `PASS`).
4. CLI commands: `jevscout runs score <run_id>` and `jevscout runs evaluations <run_id>`.
5. 104 passing tests with zero network required during automated test runs.

Next steps for this workstream:
1. Curated employer seeds: execute token harvest script against Common Crawl S3 index to build Indian tech employer catalogs across the 6 ATS feeds.
2. Web UI / Dashboard or batch evaluation reporting for top matched jobs.

Implementation has begun with a zero-runtime-dependency Python package, filesystem run/artifact storage, and CLI pending-run create/show/list. Creating a record does not approve or execute a crawl. Read `CHANGELOG.md` and `docs/changes/` for behavior, test evidence, and limitations. Do not return to job-profile questions prematurely.

Since the original handoff, Python and Crawlee for Python were selected. The crawler is embedded behind a replaceable adapter; it owns its URL frontier and request retries, while JevScout schedules crawl-session and downstream processing tasks. Modularity means focused code changes, not runtime hot-swapping. Indeed and Naukri are initial target adapters whose access feasibility remains unverified. Manual login/profile reuse is planned; an optional browser console is proposed.

The collection-first milestone is approved. The latest user decision is ordinary filesystem persistence now, PostgreSQL later due hardware constraints. Initial operations are single-writer and synchronous; no distributed file queue or background worker has been implemented. The user authorized scoped delegation, regular commits of usable slices, and ongoing changelog/handoff updates. Target-source feasibility remains separate. The full overview and sequence diagrams are in [System overview](docs/system-overview.md); their database/worker topology is a later target, superseded for the first slice by the filesystem-first note.

## Read first

1. [System architecture](docs/system-architecture.md): primary architecture, seven Mermaid diagrams, confirmed boundaries, and deferred decisions.
2. [Architecture decisions](docs/architecture-decisions.md): accepted decisions from the grilling session.
3. [JEV research](docs/jev-integration.md): official provider links and verified capabilities; live API access remains untested.
4. [Job-source research](docs/job-source-research.md): official employer-scoped feed APIs and the separate problem of discovering unknown employers.
5. [README](README.md): project overview and document index.
6. [Execution plan](docs/execution-plan.md), [Changelog](CHANGELOG.md), and [Working agreement](AGENTS.md): current filesystem-first ordering, verification, delegation, and commit conventions.

[Earlier architecture/data](docs/architecture.md), [product requirements](docs/product.md), and [roadmap](docs/roadmap.md) contain initial job-focused proposals. The system architecture takes precedence. The job-source research's original first-round questions are historical, not the next agenda.

## Continuing the session

Next add the real bounded Crawlee HTTP adapter against controlled fixtures, saved response evidence, source parsing, and inspection in separate verified slices. Verify installed released APIs before pinning Crawlee; research docs can describe unreleased features. Link-enqueue filtering alone does not prevent an HTTP client following an out-of-scope redirect; verify destination/redirect enforcement before claiming scope isolation. Do not require PostgreSQL or build a distributed file scheduler to proceed. Queue/backend and recovery guarantees are later work.

Current checks use `PYTHONPATH=src python3 -m unittest discover -s tests -v`: 17 passing tests at this boundary. The local `.venv` has an editable installation; `.venv/bin/jevscout` was smoke-tested across separate create/show processes. System Python lacks pip/ensurepip; a downloaded pip zipapp in `/tmp` was used for the local editable install without changing OS packages. The standard-library module invocation works without any dependency installation. No live site is crawled by these tests or the CLI. Code and supporting docs are being committed as the first usable local slice; no push was requested with this implementation instruction.

The user values quality and maintainability without commercial-scale infrastructure. They like flowcharts and explicitly asked for more diagrams. Explain concepts plainly before asking them to choose. Keep research findings distinct from user-approved decisions. Defer detailed job sources, résumé/profile inputs, and scoring preferences until the core architecture is ready.

Agents can operate the future application under explicit user authorization. The intent is bounded execution and approved overrides rather than approval prompts for every read. Refer to the architecture's approval section rather than reinstating the earlier, superseded interpretation that every status check requires approval.

## Suggested skills

- `grilling`: installed at `/home/abhi/.agents/skills/grilling/SKILL.md`. Use for the ongoing architecture interview. Read it before continuing; ask independent decisions in rounds with recommendations and wait for answers.
- `handoff`: installed globally through `npx skills add mattpocock/skills --skill handoff --agent codex --global --yes`, at `/home/abhi/.agents/skills/handoff/SKILL.md`. Use when updating session handoff information; the user's project-folder preference takes precedence over its default location.
- `openai-docs`: use for Codex/app setup and permissions questions, not generic crawler architecture.
- `skill-installer`: use if installing additional skills. The user accepts `npx skills` installation.
- Project-local copies of `find-skills`, `grill-me`, `grilling`, `handoff`, and `tdd` are in `.agents/skills/`. Read the relevant local instructions before use. Tests cover public run-spec/store/CLI behavior; implement one red/green slice at a time.

## Delegation and progress records

Use Luna by default for small bounded implementation/review tasks. The coordinator owns integration, contracts, changelog/handoff, and commits. Every implementing agent writes its assigned `docs/changes/<task>.md`, with exact checks and limitations; no concurrent edits to central progress records. Do not allow recursive spawning, unrelated scope expansion, or child Git operations. Existing notes: `filesystem-core.md` and `filesystem-cli.md`.

Use only skills actually available in the new session; inspect their instructions through the provided file-reading tools if no dedicated Skill tool exists. Do not invoke the interview merely because this handoff mentions its trigger phrases; continue it when requested.

## Git and execution environment notes

The environment is WSL Debian. Earlier push failures came from restricted sandbox networking and system SSH files appearing owned by `nobody`; they were not proof of broken GitHub credentials. After permissions allowed escalation, ordinary SSH Git operations outside the sandbox succeeded. Do not change system ownership or DNS based on those earlier symptoms.

Successful fetch/push commands used the execution tool's approved `require_escalated` mode. If a new session encounters the same sandbox-related SSH/network failure, follow its active permission instructions and request escalation where allowed. Do not assume a fresh session has identical permissions.

No credentials belong in this document or project. Run data, artifacts, environments, and generated build metadata are ignored by Git. Atomic replacement prevents partially written individual files from normal interrupted writes; it is not a multi-file transaction, a power-loss guarantee, a job queue, or crash resume. Use a trusted local directory with one writer.

Full Docker verification: `docker compose run --rm test` ran 121 tests in 51.873s with no skips: 115 passing test methods, six known regression methods failing (40 subtest/assertion failures and two lock errors). No new integration failures.
