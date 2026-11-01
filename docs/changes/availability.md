# Listing availability checks

Availability checks are a separate, explicit operation. Call
`AvailabilityChecker.check(urls, requested=True)` with one to 100 listing URLs;
the checker makes one bounded request per URL and stores the latest results in
an `AvailabilityStore` JSON file independent of job decisions and crawl runs.

Only HTTP 200 means available. HTTP 404 and 410 mean unavailable. Redirects
are never followed, and redirects, other HTTP statuses, timeouts, scope errors,
and transport failures are recorded as unknown. Every record includes the URL,
status when available, UTC check time, and a machine-readable reason when the
result is not conclusive.

The default transport uses the scoped Crawlee HTTP transport: DNS answers must
be globally routed, connections use a validated numeric address, proxies are
disabled, requests are restricted to the checked origin, and redirects remain
disabled. A requester can be injected for controlled fixtures without network
access.

Coordinator integration: the local API exposes `/api/availability` and an explicitly approved, bounded `/api/availability/check`; `/api/jobs` returns saved status and sorts reachable URLs first. The UI shows a Check needed filter and can start up to 100 checks, prioritizing unchecked URLs. Background checks are sequential, with one second between URLs. This is page reachability, not confirmation a position remains open.
