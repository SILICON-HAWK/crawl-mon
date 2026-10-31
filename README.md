# JevScout

A modular web crawler with typed AI classification. Job discovery and personalized fit ranking are its first use case.

JevScout discovers job listings, extracts consistent job data, and sends each job together with your profile and preferences to TypeSafe AI's JEV model for fit classification. The result is a ranked collection of jobs with explanations and application links.

## Current status

The local collection slice creates a run, collects pages through Crawlee, saves evidence, extracts JSON-LD JobPosting records, and exposes results through the CLI. Storage is ordinary local files; no database service is needed. Creating a request does **not** start or approve a crawl. Execution is synchronous and explicitly approved through the calling host. JEV, browser login, and Indeed/Naukri adapters are not implemented. See [the runnable collection example](docs/local-collection.md).

## Run locally

From this repository root, using Python 3.11 or newer:

```bash
PYTHONPATH=backend/src python3 -m jevscout --data-dir ./data runs create \
  --seed https://example.com/careers --max-pages 10 --max-depth 1
PYTHONPATH=backend/src python3 -m jevscout --data-dir ./data runs list
PYTHONPATH=backend/src python3 -m jevscout --data-dir ./data runs show RUN_ID
```

Replace `RUN_ID` with the UUID returned by `create`. Success responses are JSON on stdout; diagnostics go to stderr. Put `--debug` and `--data-dir` before `runs`. An editable package install also exposes the `jevscout` command when Python packaging tools are available:

```bash
python3 -m pip install -e ./backend
jevscout --data-dir ./data runs list
```

Run the dependency-free behavior checks:

```bash
PYTHONPATH=backend/src python3 -m unittest discover -s backend/tests -t backend -v
```

Run records and saved artifacts live under `data/`, which is excluded from Git. Use a trusted local storage directory with one writer. Filesystem persistence does not implement a shared task queue, background execution, multi-container coordination, or crash resume. PostgreSQL and a maintained queue backend are deferred. See [Changelog](CHANGELOG.md) for verified slice status and [Execution plan](docs/execution-plan.md) for remaining work.

Install the optional HTTP collection dependency set and run all collection checks:

```bash
python3 -m pip install -e './backend[crawl]'
python3 -m unittest discover -s backend/tests -t backend -v
```

Use a virtual environment for package installation. Core record/query/parser operations remain dependency-free; collection tests are skipped when the optional Crawlee extra is absent. No browser downloads or database are required for this HTTP-only slice.

## First version

- Crawl a small, configured set of public job sources.
- Extract and deduplicate job listings while preserving source links.
- Accept your professional profile and job preferences.
- Classify job fit through JEV and build summaries from dimension scores and extracted evidence.
- Browse ranked results and filter by job details and classification.

## Documentation

- [Local collection walkthrough](docs/local-collection.md): runnable fixture, inspection, offline extraction, and current limits.
- [Execution plan](docs/execution-plan.md): implementation slices, test boundaries, decision gates, and scoped delegation.
- [Complete system overview](docs/system-overview.md): full architecture graph with subgraphs and an end-to-end sequence diagram.
- [System architecture](docs/system-architecture.md): consolidated architecture with component, pipeline, worker, approval, and results diagrams.
- [Architecture decisions](docs/architecture-decisions.md): confirmed general-purpose design and open choices; takes precedence over earlier job-focused proposals.
- [JEV integration research](docs/jev-integration.md): verified model capabilities and API documentation.
- [Job-source research](docs/job-source-research.md): public collection interfaces and discovery limitations.
- [Product requirements](docs/product.md): user journey, scope, and acceptance criteria.
- [Architecture and data](docs/architecture.md): pipeline, proposed records, and JEV boundary.
- [Implementation roadmap](docs/roadmap.md): build phases and decisions still needed.

## Start here

Python and Crawlee are selected. Start with local filesystem persistence, then CLI-driven collection, saved evidence, structured extraction, and inspection; add JEV afterward. The target architecture is containerizable, with a focused core library, CLI/MCP/API adapters, bounded workers, persistent runs, and an optional results UI. PostgreSQL is the intended later backend. Target-site feasibility is validated separately.

See [Subsystem test suites](backend/tests/README.md) for core, crawler, database, Docker, and utility checks.

## Backend layout

The Python package lives in `backend/src/jevscout`: `core` defines run models and crawler contracts; `application` coordinates use cases; `modules/jobs` contains job extraction and scoring; `adapters` contains Crawlee and source integrations; `storage` contains persistence implementations; and `interfaces` contains the CLI. Python imports have moved to these paths.
