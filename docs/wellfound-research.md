# Wellfound source access research

Research checked 2026-10-31 against Wellfound's official public pages.

## Decision

Do not add a Wellfound collector or parser to JEVScout at this time. Wellfound's
public Terms prohibit copying, disclosing, or distributing site content except
where expressly permitted, including automated or non-automated harvesting,
collection, or scraping. The terms also grant automated copying only to public
search engines for publicly searchable index materials (not caches or
archives). JEVScout is not operating as a public search engine. The public
robots file leaves some job pages crawlable, but that is not permission to
collect and reuse their content under the Terms.

No documented, public jobs listing API or feed was found in Wellfound's
official developer/help material. Wellfound's documented remote MCP server at
`https://wellfound.com/api/mcp` is an OAuth-protected recruiter integration for
reviewing and acting on applicants. It requires an active Essentials or Recruit
Pro subscription, a seat, and recruiter permissions. Its described data scope
is application/candidate information for companies the recruiter may access;
it is not a public job-discovery API. No authenticated access was attempted.

Since there is no verified permitted source and no approved fixture set, a
parser would merely encode an undocumented, unsupported payload assumption.
The adapter, tests, and parser are intentionally not created. Revisit only if
Wellfound publishes/authorizes a public job feed or grants written permission
for JEVScout's collection and reuse.

## Verified official evidence

- [General Terms](https://wellfound.com/terms), section III, clause 4 prohibits
  copying/distributing content except as expressly permitted, including by
  harvesting, collection, or scraping. Clause 6 restricts automated access that exceeds human browsing load; it separately grants public search engines permission to copy publicly searchable index material.
  Sections II and IV also reserve content rights and restrict copying or
  disclosure.
- [Wellfound robots.txt](https://wellfound.com/robots.txt) is for `User-agent:
  *`. It disallows `/_jobs/`, `/search`, `/auth/`, `/u/`, and selected query
  forms such as `*?role=*` and `*?jobId=*`. It does not disallow every public
  job page. This is a crawl directive, not an express license to harvest or
  reuse page contents.
- [Jobs Terms](https://wellfound.com/terms/jobs), section II, describe the
  candidate-facing job search as a service accessed through Wellfound and the
  employer ATS integrations as synchronization functionality. They do not
  describe a public feed for third-party job discovery.
- [Connect Wellfound to your AI assistant](https://help.wellfound.com/article/1219-connect-wellfound-to-your-ai-assistant),
  last updated 2026-10-28, documents `https://wellfound.com/api/mcp` with
  OAuth. It specifies an eligible recruiter subscription/seat and permissions,
  and describes reviewing applicants, not harvesting public job listings.

## Future adapter contract

If Wellfound supplies a permitted feed/API and representative payloads, an
adapter should follow existing source parser conventions:

```python
parse_wellfound_feed(
    payload_json: str,
    source_url: str,
    artifact_ref: str,
    india_only: bool = True,
) -> list[dict[str, Any]]
```

The registry should dispatch only from documented endpoint identity or a
verified payload shape. Location and technical-stack filters should preserve
unknown values instead of treating them as a negative match. This is a future
contract only; no network access path is currently supported.
