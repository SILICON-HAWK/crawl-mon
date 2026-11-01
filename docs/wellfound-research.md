# Wellfound source investigation and diagnostic

Updated 2026-11-01 after the user requested a new attempt. This is a limited diagnostic, not a supported automated Wellfound integration.

## What worked

Wellfound exposes a public role-specific page at `/role/l/software-engineer/india`. One authorized diagnostic request through the environment's configured proxy returned an HTML page containing role links and employer names. The saved-page parser `adapters/sources/wellfound.py` extracted 38 listings, of which 32 matched the project's technical-title filter. The diagnostic was imported as run `a13b3709-095d-446c-af9e-ec956b448087`, with `engine=manual-proxy-diagnostic` recorded in its execution report. This was not an automated Crawlee session.

The parser uses observed, undocumented page markup. It extracts listing title, employer and link only; salary and location are unknown and are not inferred from the page URL. Markup may change without notice. It is deliberately limited to Wellfound's exact domain and `/role/` or `/location/` pages, and operates on already saved HTML. A strict India-only extraction excludes records whose location is unknown.

## Access and integration gaps

A bounded Crawlee attempt (run `41fa6db1-44a5-47b5-ad54-d8f7f4cce6f5`) timed out without saving a page. Direct no-proxy access also timed out inside and outside the sandbox, while the environment proxy returned HTTP 200. The scoped Crawlee transport currently disables proxies to enforce destination validation and DNS pinning. Automatically using a proxy would need an adapter design that preserves those controls; don't silently enable environment proxies or bypass access controls.

[Wellfound's General Terms](https://wellfound.com/terms), section III, restrict copying or distributing content, including harvesting and scraping, except as expressly permitted; its [robots file](https://wellfound.com/robots.txt) disallows several paths and query forms. Confirm the applicable authorization before relying on automated collection. Wellfound's documented [MCP integration](https://help.wellfound.com/article/1219-connect-wellfound-to-your-ai-assistant) concerns recruiter-authorized applicant workflows, not a documented candidate-facing job-discovery feed. No authenticated access or CAPTCHA bypass was attempted.

Next steps: clarify source authorization, design and test a scoped proxy-capable transport if needed, collect representative permitted fixtures, and only then add a bounded automated Wellfound source workflow. Preserve unknown location/salary and do not assume a returned page or listing is still open.
