# Tech employer feed research

Researched November 1, 2026. Remote OK official feed documentation and one
public `?tag=dev` JSON response were inspected. No credentials or private data
were used.

## Candidate: Remote OK public feed

Remote OK documents free unauthenticated JSON and RSS feeds, filterable by tag
(for example `?tag=dev` or `?tags=dev,python`). Its terms ask aggregators to
mention Remote OK and link to the original job post; its API payload also
includes a legal notice requiring a follow link to Remote OK. The parser keeps
the feed URL, a Remote OK source link, and each job's original posting URL in
the normalized record. Any product that renders these records must display the
Remote OK source link without `nofollow` and make each individual posting
clickable. Remote OK also prohibits using its logo without written permission;
this integration uses its name only.

The `?tag=dev` response is a JSON array. The first entry is metadata/legal
notice; subsequent records expose fields including `position`, `company`,
`location`, `date`, `epoch`, `url`, `apply_url`, `salary_min`, `salary_max`,
`description`, and `tags`. It is a remote-jobs feed, but an empty location is
possible; unknown location stays unknown and is not counted as India eligible.
The `dev` tag is a discovery filter rather than proof every returned role is a
software position (e.g. a role can be tagged `dev` and sales). Domain matching
and qualification remain downstream responsibilities.

Official reference:

- [Remote OK public API and RSS feed guidance](https://remoteok.featurebase.app/help/articles/3140840-is-there-an-api-or-rssjson-feed-of-remote-jobs)

## Discovery versus extraction

The tag query narrows job records from a third-party board; it is not an
employer directory or a source of employer ATS board identifiers. It supports
job discovery and extraction, not seed discovery for the employer-scoped ATS
feeds. Existing employer token discovery is documented in
[Career site feeds](career-site-feeds.md) and [Job-source research](job-source-research.md).

## Adapter integration contract

`parse_remoteok_feed(payload_json, source_url, artifact_ref, india_only=True)`
is a pure saved-payload parser. It returns the repository's normalized job
dictionaries and adds `source_name="Remote OK"` and
`source_link="https://remoteok.com/?ref=jevscout"` to the usual source URL and
artifact provenance. It keeps `original_job_url` separately from
`application_url`, which may be an external application target. It can be
called by the feed registry with `india_only=...`; registry routing and network fetching were not changed in
this task. Empty or malformed data returns an empty list. For broad discovery
use `india_only=False`; absent locations remain `None` and `is_india=False`.
The registry / display integration must preserve the follow attribution link.
