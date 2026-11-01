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

For the local dashboard and bounded pipeline, see [Frontend MVP](docs/frontend-mvp.md).

## Run a built local app

Build and serve a production frontend snapshot together with the FastAPI backend:

```sh
make deploy-built
```

This uses `frontend/dist-built` for the built snapshot and listens on all IPv4 interfaces (`0.0.0.0:8081`) by default. It does not replace the Vite development server (`5173`) or the existing stable deployment (`8080`). The API uses `data/live-trial` and `user-assets/`, so existing runs and profile data remain available. Avoid submitting concurrent write operations through multiple app instances sharing these stores; they do not provide a multi-writer guarantee. Keep the background feed refresh worker as its separate CLI process; this command does not create another feed worker. The API's explicitly submitted pipeline actions remain available.

The development API uses the same default data and user-assets directories. An explicit `JEVSCOUT_DATA_DIR` or `JEVSCOUT_USER_ASSETS_DIR` overrides those defaults, so configure both instances consistently when using custom paths.

Use `make build-built` to build without starting a server, or `make run-built` to serve an existing snapshot. Override `BUILT_PORT`, `BUILT_HOST`, `BUILT_FRONTEND_DIR`, and `DATA_DIR` when needed, for example `make deploy-built BUILT_PORT=8082`. If the selected address is occupied, startup exits with an error and leaves the existing process alone. Details and current pipeline limits are in [built deployment notes](docs/changes/built-deploy.md).

Open `http://localhost:8081` on the WSL host, or `http://<wsl-tailscale-ip>:8081` from a connected Tailscale device. Windows localhost forwarding and network firewall rules may affect access. The app has no login: listening on all interfaces can also expose it to other reachable networks. To restrict it to localhost, use `make deploy-built BUILT_HOST=127.0.0.1`; to restrict it to Tailscale, set `BUILT_HOST` to the WSL Tailscale IP.

## Tech feed and listing checks

The Runs page can add the public **Remote OK** developer-tagged feed, or recognized employer-feed candidates from saved job links. Remote OK results retain a link to the original posting and attribution to Remote OK. The tag is a discovery hint; the shared technical-job filter still classifies extracted titles. The live feed returned 99 listings in the initial bounded run, with 25 matching the current technical filter. Feed content and availability change over time.

Employer-feed candidates are inferred only from known Greenhouse, Ashby, and Lever job-board URL patterns; they are unverified suggestions, not proof the employer is hiring or a general web search. Review a candidate and explicitly start a pipeline to fetch its current board. Unknown employer sites remain unresolved. Company names come from explicit source fields or a small configured board mapping; unknown names are not guessed.

On Jobs, **Check listings** starts an explicit background check of up to 100 application URLs; repeat to cover additional unchecked jobs. HTTP 200 means the page responded, not that the position is definitely open. HTTP 404/410 is marked not found; redirects, rate limits, other responses and network failures are inconclusive. The API stores results separately, prioritizes reachable pages, and leaves issues visible in the **Check needed** filter. Checking is sequential and can take time. The source checks do not follow redirects and reject local/private network destinations.

See [tech-source research](docs/tech-source-research.md) and [listing availability notes](docs/changes/availability.md). The Remote OK API is public and requests should be modest; follow its [source documentation](https://remoteok.featurebase.app/help/articles/3140840-is-there-an-api-or-rssjson-feed-of-remote-jobs) and attribution requirements.

## Background feed refresh

Start the optional, explicitly approved CLI worker from the repository root:

```sh
PYTHONPATH=backend/src .venv/bin/python -m jevscout.application.feed_refresh \
  --data-dir data/live-trial --approve
```

The worker refreshes five previously configured public feeds: Remote OK (`dev`), SonicWall, Firstwork, TransPerfect and Nexthire. It runs one feed at a time, at most one feed page per run, at least 12 hours between successful refreshes of the same feed, at least 60 seconds between feed starts, and waits 24 hours after a failed or partial refresh. It makes no immediate request retries. Within a scheduled crawl it waits at least two seconds between same-origin HTTP requests and honors integer `Crawl-delay` values returned in robots.txt when they are larger. Robots allow/disallow still applies. These limits apply to this worker; manual crawls are separate.

To inspect or stop it, from another terminal:

```sh
PYTHONPATH=backend/src .venv/bin/python -m jevscout.application.feed_refresh --data-dir data/live-trial --status
PYTHONPATH=backend/src .venv/bin/python -m jevscout.application.feed_refresh --data-dir data/live-trial --stop
```

The stop is graceful; an in-flight request may finish first. A local lock prevents a second refresh worker using the same data directory, and its schedule survives a worker restart. It does not install a system service or automatically restart when WSL or the session stops. It collects and extracts records but does not run the decision model. Saved snapshots are retained, so disk usage will grow over time. The source list is fixed in `backend/src/jevscout/application/feed_refresh.py` for this first version; change it deliberately rather than pointing the worker at arbitrary sites.

A limited Wellfound saved-page diagnostic is documented in [Wellfound research](docs/wellfound-research.md). Automated collection is not available; the diagnostic uses the environment proxy and the scoped crawler currently disables proxies.
