# Implementation roadmap

## 1. Confirm inputs and interfaces

- Use the verified [JEV integration research](jev-integration.md) and test an authenticated request.
- Define the user's profile, preferences, and hard constraints.
- Select one or two initial job sources and confirm permitted access methods.
- Choose the implementation stack and first results interface.
- Agree on classification labels, ordering, and how unknown values affect results.

Outcome: a concrete specification for one job-to-evaluation flow.

## 2. Build job collection

- Implement bounded discovery and fetching for the initial sources.
- Extract and normalize jobs with source provenance.
- Persist jobs, crawl status, and duplicate relationships.
- Support retries and basic freshness tracking.

Outcome: inspectable, deduplicated job records from a small crawl.

## 3. Add personalized evaluation

- Add versioned profile/preferences input.
- Implement the JEV adapter using its confirmed contract.
- Validate and persist outputs with evaluation provenance.
- Add bounded retries and reevaluation when inputs change.

Outcome: jobs classified against the user's information with clear failure states.

## 4. Make results useful

- Display ranked jobs, fit explanations, gaps, and application links.
- Add filters for supported listing fields and fit categories.
- Expose stale listings, unknown values, and pending/failed evaluations.
- Compare a small sample against the user's own judgments and tune the matching inputs.

Outcome: a usable first version for discovering and assessing jobs.

## Later possibilities

Saved jobs and dismissals, scheduled crawls, new-match notifications, additional source adapters, and feedback-driven matching improvements. These require separate scope decisions after the first version works.

## Open decisions

| Decision | Current state |
| --- | --- |
| JEV API and model contract | Official docs verified; live API access pending |
| Initial job sources | To be selected |
| User profile and preferred roles | To be supplied |
| Definition of a good fit | Personalized; detailed criteria pending |
| Stack, database, and hosting | Not selected |
| First interface: CLI, web, or another format | Not selected |
| Crawl schedule and scale | Start manually with bounded runs; exact limits pending |
| Profile/provider data retention | To be confirmed before real profile submission |

## Next implementation milestone

Take one job listing, extract its details, evaluate it against a sample profile through the confirmed JEV API, and inspect the stored result. Expand to automated discovery after that path is verified.
