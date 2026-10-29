# JevScout

A modular web crawler with typed AI classification. Job discovery and personalized fit ranking are its first use case.

JevScout discovers job listings, extracts consistent job data, and sends each job together with your profile and preferences to TypeSafe AI's JEV model for fit classification. The result is a ranked collection of jobs with explanations and application links.

## Current status

Project definition and planning. No crawler or model integration has been implemented yet. Official JEV documentation is verified in [JEV integration research](docs/jev-integration.md). Live API access remains untested.

## First version

- Crawl a small, configured set of public job sources.
- Extract and deduplicate job listings while preserving source links.
- Accept your professional profile and job preferences.
- Classify job fit through JEV and build summaries from dimension scores and extracted evidence.
- Browse ranked results and filter by job details and classification.

## Documentation

- [Architecture decisions](docs/architecture-decisions.md): confirmed general-purpose design and open choices; takes precedence over earlier job-focused proposals.
- [JEV integration research](docs/jev-integration.md): verified model capabilities and API documentation.
- [Job-source research](docs/job-source-research.md): public collection interfaces and discovery limitations.
- [Product requirements](docs/product.md): user journey, scope, and acceptance criteria.
- [Architecture and data](docs/architecture.md): pipeline, proposed records, and JEV boundary.
- [Implementation roadmap](docs/roadmap.md): build phases and decisions still needed.

## Start here

Finish the architecture discussion before selecting the implementation stack and job-specific settings. The project is containerizable, with a focused core library, CLI/MCP/API adapters, bounded workers, persistent runs, and an optional results UI. No technology stack has been selected.
