# JevScout

A modular web crawler with typed AI classification. Job discovery and personalized fit ranking are its first use case.

JevScout discovers job listings, extracts consistent job data, and sends each job together with your profile and preferences to TypeSafe AI's JEV model for fit classification. The result is a ranked collection of jobs with explanations and application links.

## Current status

The first local slice creates and inspects filesystem-backed run requests. Python has no runtime dependencies for this slice; no database service is needed. Creating a request does **not** start or approve a crawl. Crawlee execution, extraction, and JEV integration remain next steps. Official JEV documentation is verified in [JEV integration research](docs/jev-integration.md); live API access remains untested.

## Run locally

From this repository root, using Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m jevscout --data-dir ./data runs create \
  --seed https://example.com/careers --max-pages 10 --max-depth 1
PYTHONPATH=src python3 -m jevscout --data-dir ./data runs list
PYTHONPATH=src python3 -m jevscout --data-dir ./data runs show RUN_ID
```

Replace `RUN_ID` with the UUID returned by `create`. Success responses are JSON on stdout; diagnostics go to stderr. Put `--debug` and `--data-dir` before `runs`. An editable package install also exposes the `jevscout` command when Python packaging tools are available:

```bash
python3 -m pip install -e .
jevscout --data-dir ./data runs list
```

Run the dependency-free behavior checks:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run records and saved artifacts live under `data/`, which is excluded from Git. Use a trusted local storage directory with one writer. Filesystem persistence does not implement a shared task queue, background execution, multi-container coordination, or crash resume. PostgreSQL and a maintained queue backend are deferred. See [Changelog](CHANGELOG.md) for verified slice status and [Execution plan](docs/execution-plan.md) for remaining work.

## First version

- Crawl a small, configured set of public job sources.
- Extract and deduplicate job listings while preserving source links.
- Accept your professional profile and job preferences.
- Classify job fit through JEV and build summaries from dimension scores and extracted evidence.
- Browse ranked results and filter by job details and classification.

## Documentation

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
