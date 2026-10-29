# Complete 6-Provider ATS Feeds, Quality Guards & Token Harvester

Integrated full coverage of the 6 validated public ATS providers identified in the Open ATS Feed measurement (Greenhouse, Lever, Ashby, Breezy HR, Recruitee, Teamtailor), empirical quality/acronym guards, and Common Crawl S3 token harvesting.

## Files
- `src/jevscout/feeds/breezy.py`: Breezy HR feed adapter (`parse_breezy_feed`).
- `src/jevscout/feeds/recruitee.py`: Recruitee offers feed adapter (`parse_recruitee_feed`).
- `src/jevscout/feeds/teamtailor.py`: Teamtailor jobs feed adapter (`parse_teamtailor_feed`).
- `src/jevscout/feeds/harvester.py`: Common Crawl CDX/SURT token extraction and unauthenticated API endpoint builder.
- `src/jevscout/feeds/quality.py`: Description CDN sanitizer, technical title scoping for acronyms (e.g., `dbt`, `PHP`), and department explosion mitigation (>25 threshold).
- `src/jevscout/feeds/registry.py`: Unified detection for all 6 ATS formats via URL and payload heuristics.
- `src/jevscout/feeds/greenhouse.py`: Updated with description sanitization and debug logging with URL redaction.
- `src/jevscout/feeds/lever.py`: Updated with description sanitization and debug logging with URL redaction.
- `src/jevscout/feeds/ashby.py`: Updated with description sanitization and debug logging with URL redaction.
- `tests/fixtures/feeds/breezy_sample.json`: Breezy HR fixture.
- `tests/fixtures/feeds/recruitee_sample.json`: Recruitee fixture.
- `tests/fixtures/feeds/teamtailor_sample.json`: Teamtailor fixture.
- `tests/test_breezy_feed.py`: 4 tests for Breezy HR.
- `tests/test_recruitee_feed.py`: 4 tests for Recruitee.
- `tests/test_teamtailor_feed.py`: 4 tests for Teamtailor.
- `tests/test_harvester.py`: 5 tests for SURT parsing, slug validation, and API endpoint construction.
- `tests/test_quality_guards.py`: 5 tests for quality sanitization, acronym scoping, and department counts.
- `tests/test_feed_registry.py`: 4 tests for 6-provider URL and payload dispatch.

## Checks & Verification
- Unit & integration checks: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` passed all 90 tests in 25.900s with 0 failures and 0 errors.
- Verification covered:
  - All 6 ATS formats correctly parsed with schema.org `JobPosting` compatibility.
  - Strict India location filtering across all 6 providers.
  - CDN links and script tags stripped to prevent false-positive stack matches.
  - Diagnostic debug logging cleanly avoids leaking raw source URLs.
  - Harvester extracts company tokens from SURT keys and constructs exact unauthenticated API endpoints.

## Limitations
- Lever requires honoring `Crawl-delay: 1` (1 req/sec) when running active network sweeps.
- SmartRecruiters, Personio, and Workable remain refused per robots.txt RFC 9309 compliance and severe throttling.
