# Local collection walkthrough

This is a working collection/extraction slice, not the entire target system. It uses real Crawlee HTTP collection and a controlled fixture. Indeed/Naukri access and site-specific navigation remain separate work.

## Setup

Use Python 3.11+ in a virtual environment, then install the project and HTTP extra:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e './backend[crawl]'
```

The dependency set pins Crawlee 1.11.0, HTTPX2 2.16.0, and HTTPCore2 2.16.0. No browser binaries or PostgreSQL service are needed. On distributions that omit venv/pip, enable their Python packaging support first, or use an existing package-managed environment. The record-only CLI also runs with `PYTHONPATH=backend/src python3 -m jevscout` without package installation.

## Collect the controlled fixture

From the repository root, start the fixture in one terminal:

```bash
python3 -m http.server 8765 --bind 127.0.0.1 --directory backend/tests/fixtures
```

In a second terminal, create a request:

```bash
.venv/bin/jevscout --data-dir ./data runs create \
  --seed http://127.0.0.1:8765/ --allow-local \
  --max-pages 3 --max-depth 1 --timeout-seconds 30
```

Copy the returned UUID into `RUN_ID` below. Creation only saves a pending request. The `allow_local` setting is persisted and permits loopback fixtures; it does not allow arbitrary private-network destinations.

```bash
RUN_ID='paste-returned-uuid-here'
.venv/bin/jevscout --data-dir ./data runs execute "$RUN_ID" --approve
.venv/bin/jevscout --data-dir ./data runs show "$RUN_ID"
.venv/bin/jevscout --data-dir ./data runs pages "$RUN_ID"
.venv/bin/jevscout --data-dir ./data runs results "$RUN_ID"
.venv/bin/jevscout --data-dir ./data runs report "$RUN_ID"
```

Expected: two saved pages and two JobPosting records, titled `Platform Engineer` and `Remote Product Designer`. Page evidence, source URLs, and artifact references are preserved. The duplicate link to the job page is fetched only once. `report` includes the exact approved specification, engine version, timestamps, page/item counts, final failures, and outside-scope candidates.

Success responses are JSON on stdout. Operational logs and redacted debug diagnostics go to stderr. Put `--debug` before `runs` to enable application diagnostics; raw framework request traces are suppressed.

## Inspect evidence and rerun extraction offline

Use an `artifact_ref` from `pages` or `results`:

```bash
.venv/bin/jevscout --data-dir ./data runs artifact "$RUN_ID" --ref 'pages/PASTE_HASH.html'
```

Stop the fixture server, then rerun extraction:

```bash
.venv/bin/jevscout --data-dir ./data runs extract "$RUN_ID"
.venv/bin/jevscout --data-dir ./data runs results "$RUN_ID"
```

This reads saved HTML only; it does not import the crawler, contact the source, or require the `[crawl]` extra. The result set is deterministically replaced using the same parser version. Saved page observations remain intact. No JEV calls occur.

## Execution behavior

- Only pending runs can execute. For another collection, create a new run; completed runs are not silently recrawled.
- `--approve` asserts explicit user approval through the calling host. It is not user authentication or proof that an autonomous agent obtained consent. A trusted approval UI is not implemented.
- Crawl scope is the exact HTTP(S) origin of the seeds, not a path-prefix or role filter. Source-specific navigation comes later. Redirects are not followed automatically: permitted same-origin targets are queued at the next depth, while outside-origin targets are recorded without fetching them.
- The connection backend validates resolved addresses and connects to a selected numeric allowed address, preserving the original Host/TLS identity. Non-public addresses are rejected unless explicit loopback access is configured. Proxies/environment proxy settings are disabled for this slice.
- Crawlee owns the URL frontier, duplicate filtering, depth limit, and one retry after an initial request failure. Page limits are not limits on every network operation: robots retrieval and retries add requests. Only one HTTP request executes at a time.
- Robots-disallowed requests are reported as failures. Standard robots allow/disallow is respected; Crawl-delay scheduling is not implemented in this adapter.
- `completed` means the bounded collection and extraction finished without reported request failures. A page/depth limit is part of the requested scope, not a claim that the entire site was exhausted. Mixed outcomes return `partial`; no successful pages plus failures returns `failed`. Partial/failed execution exits nonzero while preserving saved evidence and any extracted results.
- Ctrl+C records `cancelled` and exits 130. Overall timeout records failure or partial results. Cancellation prevents new saves/requests once observed but cleanup may wait for in-flight work within its navigation timeout (at most 30 seconds). This is not instantaneous process termination.
- Only one local execution/extraction operation may hold the advisory lock for a data root. POSIX/WSL is the tested execution platform. Reads remain available. The lock is not a shared queue or distributed lease.
- SIGKILL/power-loss crash resume is not implemented. A killed process may leave a run marked `running`; saved evidence remains but recovery requires a separate future operation. Atomic file replacement is not a multi-file transaction.

## Current extraction and collection limits

The parser extracts existing schema.org JobPosting JSON-LD. It does not infer jobs from arbitrary page text, score fit, verify applications, or implement board-specific selectors. Unknown fields remain null; invalid/malformed scripts and untitled records are skipped. Zero extracted jobs is a valid outcome, not proof that a page contains no jobs.

The engine is HTTP-only: no JavaScript rendering, login flow, manual browser console, or proxy rotation is shipped. Saved HTML is currently decoded as UTF-8 with replacement for invalid bytes. Response-size/decompression limits and stronger production resource accounting remain future work; use known sources and bounded fixture runs rather than treating this as an unrestricted internet service.

The transport backend and cancellation context use version-pinned framework extension points, including a private HTTPX transport integration. Keep dependency upgrades behind adapter tests. The core and public CLI data types do not depend on Crawlee types.

## Verification

```bash
PYTHONPATH=backend/src .venv/bin/python -m unittest discover -s backend/tests -v
```

The suite uses local HTTP servers plus external DNS/socket-boundary simulations; no Indeed/Naukri credentials, live job boards, or JEV credits are required. It covers traversal, duplicate links, depth/page limits, redirects, default local denial, robots denial, bounded retries, metadata/result storage, explicit approval, partial results, timeout/cancellation, debug redaction, and offline extraction.
