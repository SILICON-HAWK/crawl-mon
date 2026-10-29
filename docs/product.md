# Product requirements

## Purpose

Help the user find relevant jobs without manually searching many websites and comparing every listing against their background. “Good job” means a good fit for this user's information and preferences, rather than a universal judgment about an employer.

## Primary workflow

1. The user supplies a professional profile and job preferences.
2. The user configures job sources and search criteria.
3. JevScout discovers and fetches job pages.
4. It extracts job details and merges duplicate discoveries.
5. It passes the job and relevant profile information to JEV.
6. The user reviews ranked jobs, fit explanations, gaps, and original application links.

## Profile and preferences

Proposed inputs include résumé text or a professional summary, skills, experience, desired roles, seniority, preferred locations, remote/hybrid/on-site preferences, salary expectations with currency and pay period, work authorization constraints, and dealbreakers.

Distinguish required constraints from preferences. Missing information must remain unknown; it must not be treated as a mismatch or invented. Collect only information needed for matching. A résumé file upload is a possible later input method; pasted text is sufficient for the first version.

## First-version scope

- One user's profile and preferences.
- A small, explicit list of public job sources and crawl limits.
- Job discovery, extraction, normalization, deduplication, and persistence.
- JEV fit classification with dimension-based summaries and uncertainty. Jev does not generate prose; summaries use application templates and extracted evidence.
- Ranked results with filters and links back to the original listings.
- Visible crawl and classification status, including errors and last-check times.

## Outside the first version

- Automatic applications or contacting recruiters.
- Crawling the entire internet without configured source boundaries.
- Access behind logins, paywalls, or access controls.
- Multi-user accounts, billing, and résumé generation.

## Result presentation

Each result should show the role, company, source/application link, location and workplace type when known, salary when published, fit classification, supporting reasons, missing requirements, and when it was last checked. Show a numeric score only if JEV supplies a documented score or we explicitly define and validate a scoring scheme.

Keep model output distinct from facts extracted from the listing. Unknown salary, location, or requirements should be visible as unknown. A failed evaluation should be labeled pending or failed and excluded from scored ordering until it succeeds.

## Acceptance criteria

- A configured source yields persisted jobs with valid source URLs and extraction timestamps.
- Duplicate discoveries appear as one job with retained source provenance.
- Each successful evaluation is traceable to a job version, profile version, and model configuration.
- Results explain fit using available listing and profile information; unsupported model claims are not presented as verified job facts.
- Changes to the profile allow jobs to be evaluated again without unnecessary recrawling.
- Crawl or JEV failures are visible and can be retried without duplicating records.
- Private profile information is excluded from crawl requests and routine logs.

## Crawling behavior

Use public sources that permit automated access. Respect robots directives and source terms, identify the crawler, limit request rates and concurrency per host, honor retry guidance, and back off after failures. Prefer a source's documented feed or API when available. Do not bypass access controls. Configure URL boundaries, page/time budgets, and maximum response sizes for every crawl.
