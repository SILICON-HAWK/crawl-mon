# Job-source research

Researched October 29, 2026. Documentation review only; no live collection implemented.

## Public job feeds

| Source | Identifier and endpoint | Useful details |
| --- | --- | --- |
| Greenhouse | Board token; `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true` | GET requires no authentication. Fields include posting ID, title, location, URL, update timestamp, and optional description, departments, and offices. Prospect posts can have a null internal job ID. |
| Lever | Company site slug and global/EU instance; `GET https://api.lever.co/v0/postings/{SITE}?mode=json` | Public postings include IDs, title, categories, descriptions, application links, workplace type, and optional salary. Supports pagination and category filters, but no full-text search or internal jobs. |
| Ashby | Job-board name; `GET https://api.ashbyhq.com/posting-api/job-board/{name}?includeCompensation=true` | Public example needs no key. Includes description, locations, employment/workplace type, publication time, links, and optional compensation. Use workplace type because the remote flag includes hybrid. Exclude unlisted postings from discovery. |

Official sources:

- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board)
- [Lever Postings API](https://github.com/lever/postings-api)
- [Lever API access clarification](https://hire.lever.co/developer/support)
- [Ashby public job posting API](https://developers.ashbyhq.com/docs/public-job-posting-api)

## Implication for JevScout

These documented interfaces fetch jobs for known employers. They do not establish a global job-search or company-directory endpoint. Broad discovery therefore needs a separate way to find employer boards, such as curated seeds, search, or another discovery source. This is an architectural inference from the employer-scoped interfaces.

Public technical access does not establish blanket reuse permission. Source and employer terms still need review for the selected collection and display behavior.

## Session state

The first grilling round is awaiting user answers on intended users, target roles/locations, qualification versus preference fit, discovery breadth, and success criteria. Recommendations are provisional; no answers or implementation choices have been assumed.

Project files and research belong under `/home/abhi/work/jevscout`.
