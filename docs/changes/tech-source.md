# Remote OK source adapter

## Behavior

Added a pure parser for Remote OK's public JSON feed. It parses known job
fields, keeps source and artifact provenance, records the required Remote OK
attribution link and individual job URL, applies existing strict India
location filtering, and leaves missing locations unknown. The original job URL
is retained separately from an optional external application URL. It does not fetch
the feed or assert that every `dev`-tagged posting is a software role.

## Files

- `backend/src/jevscout/adapters/sources/remoteok.py`
- `backend/tests/feeds/test_remoteok_feed.py`
- `docs/tech-source-research.md`

## Checks

- `PYTHONPATH=src python3 -m unittest tests.feeds.test_remoteok_feed -v` — 3
  tests passed.
- Read Remote OK's official feed guidance and inspected the documented public
  `?tag=dev` JSON response to verify the payload shape and terms. No credentials
  used.

## Integration and limits

Call `parse_remoteok_feed(payload_json, source_url, artifact_ref,
india_only=True)`. Registry routing and product rendering remain coordinator
work; rendering must preserve `source_link` as a standard follow link and keep
the individual job URL available. The tag filter is not a technical-role
classifier. No employer seed discovery, fetch adapter, or live integration was
added.
