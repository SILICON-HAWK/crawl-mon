# Saved job extraction

`parse_jobs(html, source_url, artifact_ref)` now extracts schema.org `JobPosting` JSON-LD from saved HTML. It supports a single object, top-level arrays, and `@graph`; outputs a versioned record with title, optional company/location/plain-text description/application URL/date, and source/artifact provenance. It ignores malformed JSON-LD scripts and non-job or untitled records. Relative application links resolve against the source URL, credentials and non-HTTP(S) links are rejected, and a missing link falls back to a valid source URL. JSON traversal is bounded.

Files: `src/jevscout/extraction.py`, `tests/test_extraction.py`, `tests/fixtures/jobs.html`.

Check performed:

- `PYTHONPATH=src python3 -m unittest discover -s tests -p test_extraction.py` — 2 tests passed.

Limitations: this is a pure parser for JSON-LD already present in supplied HTML; it does not fetch pages, inspect rendered/browser state, or infer fields from ordinary page text. Location formatting uses available locality, region, and country fields. Live source coverage and the broader application handoff remain outstanding.
