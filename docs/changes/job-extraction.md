# Saved job extraction

`parse_jobs(html, source_url, artifact_ref)` now extracts schema.org `JobPosting` JSON-LD from saved HTML. It supports a single object, top-level arrays, and `@graph`; outputs a versioned record with title, optional company/location/plain-text description/application URL/date, and source/artifact provenance. It ignores malformed JSON-LD scripts and non-job or untitled records. Relative application links resolve against the source URL. Credentials, non-HTTP(S) links, invalid/out-of-range ports, backslashes, whitespace, and control characters are rejected. Only a missing `url` field falls back to a valid source URL; an invalid supplied value remains unknown. JSON traversal is bounded.

Files: `src/jevscout/extraction.py`, `tests/test_extraction.py`, `tests/fixtures/jobs.html`.

Check performed:

- `PYTHONPATH=src python3 -m unittest discover -s tests -p test_extraction.py` — 3 tests passed, including malformed/out-of-range ports, backslash/control characters, and no fallback for invalid supplied URLs.

Limitations: this is a pure parser for JSON-LD already present in supplied HTML; it does not fetch pages, inspect rendered/browser state, or infer fields from ordinary page text. Location formatting uses available locality, region, and country fields. Live source coverage and the broader application handoff remain outstanding.
