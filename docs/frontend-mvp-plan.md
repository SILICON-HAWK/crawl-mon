# Frontend and pipeline MVP plan

## Scope

Deliver a local Svelte interface and a small FastAPI adapter around existing Python operations. Provide an explicitly started, bounded background pipeline that collects configured employer feeds, extracts jobs, ranks them locally and exposes progress and results to the interface. Filesystem storage remains the default. Hosted access, multiple workers, automatic discovery across the web, authenticated browsing, and external AI inference are later work.

## Data flow and later review

```mermaid
flowchart LR
    U[User: seed URLs, limits, profile] --> A[API validates and starts pipeline]
    A --> C[Crawlee collects bounded pages]
    C --> E[Saved page evidence]
    E --> X[Feed and job extraction]
    X --> R[Offline ranking]
    R --> O[Pipeline status and results]
    O --> F[UI lists jobs and provenance]
```

At review time follow one run from the submitted inputs through approved scope, saved page references, extracted fields, profile inputs, ranking dimensions and UI output. Distinguish automatic scoring from verified facts and record errors and missing data. User assets stay private; no key or résumé content goes into logs or commits.

## Execution sequence

1. Agree API/pipeline contract and validate bounded user inputs, including approved URLs, page and time limits, and one active pipeline.
2. Build a synchronous local API for existing runs and a background pipeline adapter with observable status and safe errors.
3. Build the barebones frontend for starting a pipeline, monitoring progress and viewing jobs, score and provenance.
4. Integrate, test with controlled local fixtures and existing saved runs, check failures and concurrency, and document setup.
5. Save changelog and handoff and commit verified work. Review the entire end-to-end data transformation as a separate subsequent phase.

The first MVP does not silently crawl arbitrary feeds, submit private profiles to external services, claim crash recovery, or treat scores as verified recommendations. The API is intended for trusted local use only.
