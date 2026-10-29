# Crawlee HTTP engine

Added a real `CrawleeEngine.collect` adapter. Crawlee owns URL scheduling, duplicate filtering, depth enforcement, request retries, and the page cap. The cap applies to Crawlee's opened requests; it is not a hard cap on network operations because retries and robots.txt retrieval can add requests. The adapter stores each response's full decoded HTML, status, URL, and request depth through the synchronous callback. Redirects are not followed automatically; same-origin redirect targets are queued at the next depth, and out-of-origin links and redirect targets are recorded as candidate URLs. Requests are guarded against origins outside the seeds and against non-public resolved IPs. `allow_local=True` permits loopback only. The crawler uses an isolated filesystem storage directory under the supplied work directory and respects robots.txt. Request and robots failures increment the report count and add sanitized URL/reason attribution; request failures include the total attempt count without exception text. Callback failures stop the crawler and are re-raised to the caller. Application-task cancellation is re-raised after Crawlee's runner cleanup; the adapter also replaces Crawlee's pause-style SIGINT handler during its run so SIGINT cancels that task. Navigation and handler timeouts are bounded by the run timeout and 30 seconds.

## Files

- `src/jevscout/crawlee_engine.py`: adapter and HTTP scope guard.
- `tests/test_crawlee_engine.py`: real Crawlee runs against standard-library local HTTP servers.
- `docs/changes/crawlee-engine.md`: this implementation note.

## Checks

TDD red check: `.venv/bin/python -m unittest discover -s tests -p test_crawlee_engine.py -v` failed initially because the adapter module did not yet exist.

Green check: `.venv/bin/python -m unittest discover -s tests -p test_crawlee_engine.py -v` passed all 12 focused tests. Coverage includes duplicate URLs and max depth, the page cap, cross-origin links and redirect targets, queued same-origin redirects and depth, default loopback denial, explicit loopback allowance, robots-disallowed seeds with failure attribution, callback failure propagation without following queued links, cancellation propagation for both an outer `asyncio.wait_for` timeout and direct task cancellation, a DNS answer change from a public to private IP without connecting to the private address, and one retry followed by a reported 503 failure with two attempts. A separate local slow-server check sent SIGINT to the process and observed `CancelledError` from `collect`. The test class skips cleanly if the optional Crawlee dependency is absent.

## Limitations

This adapter is HTTP-only and does not provide browser automation, authentication, or proxy support. Peer validation is pinned into Crawlee's HTTPX transport through its private `_get_client` seam and httpcore2 connection-pool backend field. This integration relies on the pinned Crawlee 1.11.0, httpx2 2.16.0, and httpcore2 2.16.0 layout; it fails fast if that layout changes. Each connection resolves once, rejects any non-global answer (except explicitly allowed loopback), and connects to a validated numeric address while retaining the original HTTP origin for Host and TLS SNI. The orchestrator remains responsible for the overall `asyncio.wait_for` timeout. `RunSpec.allow_local` defaults to `False`.
