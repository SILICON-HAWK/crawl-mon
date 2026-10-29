# Career Site Feeds and Strict India Location Filtering

Implemented browserless, zero-credential public career site feed adapters for Greenhouse, Lever, and Ashby, featuring strict India location filtering (and India-eligible remote roles), unified feed detection, and CLI/application extraction integration.

## Files
- `src/jevscout/feeds/__init__.py`: Package init.
- `src/jevscout/feeds/location.py`: Strict India location matcher and canonical normalizer (`is_india_eligible`, `normalize_india_location`).
- `src/jevscout/feeds/greenhouse.py`: Greenhouse public board API adapter (`parse_greenhouse_feed`).
- `src/jevscout/feeds/lever.py`: Lever public postings API adapter (`parse_lever_feed`).
- `src/jevscout/feeds/ashby.py`: Ashby public job board API adapter (`parse_ashby_feed`).
- `src/jevscout/feeds/registry.py`: Unified feed auto-detection and router (`detect_feed_type`, `detect_and_parse_feed`).
- `src/jevscout/extraction.py`: Integrated feed extraction fallback and `--india-only` filtering into core `parse_jobs`.
- `src/jevscout/application.py`: Propagated `india_only` parameter through `_extract` and `extract_run`.
- `src/jevscout/cli.py`: Added `--india-only` flag to `runs results` and `runs extract` commands.
- `tests/fixtures/feeds/greenhouse_sample.json`: Real-structure Greenhouse test fixture.
- `tests/fixtures/feeds/lever_sample.json`: Real-structure Lever test fixture.
- `tests/fixtures/feeds/ashby_sample.json`: Real-structure Ashby test fixture.
- `tests/test_location_filter.py`: 6 tests for India location hubs, worldwide remote, foreign rejection, and restricted remote exclusion.
- `tests/test_greenhouse_feed.py`: 4 tests for Greenhouse extraction and India filtering.
- `tests/test_lever_feed.py`: 4 tests for Lever extraction and India filtering.
- `tests/test_ashby_feed.py`: 4 tests for Ashby extraction and India filtering.
- `tests/test_feed_registry.py`: 4 tests for URL/heuristic feed auto-detection and routing.
- `tests/test_feed_integration.py`: 2 end-to-end integration tests for feed extraction and CLI commands.

## Checks & Verification
- Unit & integration checks: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` ran all 68 tests in 25.924s with 0 failures and 0 errors.
- Verification covered:
  - Canonical tech hubs in India (Bengaluru, Hyderabad, Pune, Mumbai, Gurgaon, Noida, Delhi NCR, Chennai, etc.).
  - India-eligible remote roles (`"India - Remote"`, `"Worldwide Remote"`, `"Anywhere in the world"`).
  - Strict rejection of overseas locations (US, UK, Germany, Canada, Singapore, etc.) and non-India restricted remotes (`"Remote - US Only"`, `"Remote - EMEA"`, etc.).
  - Greenhouse, Lever, and Ashby JSON parsing, secondary location checks, unescaped HTML content, and safe URL resolution.
  - End-to-end storage persistence and CLI `--india-only` filtering on saved run results.

## Limitations
- Feeds require known employer board URLs/tokens; discovery across thousands of employers without curated seed lists requires web search or board directory crawling.
- SmartRecruiters and Workable adapters are documented in architecture docs but left as modular additions.
- Proprietary aggregator portals (Naukri, Foundit) block browserless clients and are not supported by this pure HTTP/JSON feed engine.
