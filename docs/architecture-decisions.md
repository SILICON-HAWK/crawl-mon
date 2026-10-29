# Architecture decisions

Working decisions from the architecture grilling session. Architecture is being settled before job-specific requirements or implementation. No implementation is authorized by this record.

The consolidated design and diagrams are in [System architecture](system-architecture.md).

## Confirmed

- Build a general web crawler with target-specific modules; job collection is the first use case.
- Share discovery, fetching, extraction, classification, and results persistence across modules.
- Keep stages separate, with persisted inputs, outputs, and execution status for retries and reruns.
- Start as one modular application with a database rather than separate services.
- Application code controls scheduling, execution, retries, and persistence. JEV performs focused classification decisions.
- Modules expose callable tools backed by shared execution machinery. Shared operations cover starting runs, inspecting status, cancelling, and retrieving results.
- Agents submit structured pipeline inputs and may propose JEV questions, classification labels, scoring rubrics, and weights. Validate and version that configuration.
- Starting a run returns a run ID promptly. Background execution belongs to the application; the agent can subsequently monitor and retrieve results.
- User clarification supersedes approval for every read: explicitly approve work and approval overrides, then permit execution and observation within that authorization. The purpose is bounded agent execution rather than repeated approval prompts.
- Agents may propose follow-up runs, subject to user approval. Preserve parent-run and initiator provenance.
- Keep a focused core application library separate from CLI, MCP, HTTP, UI, and worker entry points. Interfaces share application operations rather than duplicating business rules.
- Support container deployment, persistent storage, and an optional UI. The UI initially covers approvals, run submission/progress/cancellation, and a results explorer.
- Organize results as runs, collected items, extracted data, and versioned JEV decisions with source/application links. Custom UI work is deferred.
- Module declarations describe configuration, actions, and result types for future UI use.
- Approval mode is deployment configuration. Agents may change it only through an explicitly user-approved configuration operation, never unilaterally through run inputs.
- Application-managed and host-delegated approval are supported design modes. Delegating approval does not remove resource limits.
- Enforce approved limits on concurrency, runtime, page collection, and model usage. Agents submit managed work rather than spawning arbitrary workers.
- Persist accepted runs and pending work in the database for recovery. CLI supports background submission and waiting for completion.
- Add structured operational logs and opt-in debug logs at meaningful boundaries. Correlate by run/task/stage IDs; redact credentials, profile contents, and page bodies. Record stage transitions, retries, failures, cancellation, budget exhaustion, approval changes, and model request metadata.

## Execution topology

All application instances initially run on the same machine, potentially in separate containers. CLI/MCP/API adapters call the core submission/query layer. Instances share a durable database-backed queue; bounded workers claim tasks and persist progress and results. The UI is optional. Remote client connections and authentication are deferred behind a future adapter.

Separate code boundaries do not require separate network services. Worker startup is explicit and managed rather than triggered once per submission. PostgreSQL with a maintained queue library is the current recommendation, not a finalized stack decision. Queue-library selection and alternative execution designs remain under discussion.

## Next architecture decisions

- Approval is bound to exact structured inputs; the detailed trusted approval interaction remains to be designed.
- Exact mechanisms for enforcing shared budgets and approved execution scope.
- Select the durable queue implementation for the confirmed Python runtime after reviewing tradeoffs.
- Detailed schemas and compatibility rules for persisted stage outputs and module interfaces.

## Confirmed pipeline and worker boundaries

- Use a maintained database-backed queue library. Choose the implementation after selecting the core language; do not implement a custom queue engine.
- A run represents one approved request. Tasks are smaller execution units within that run, created as discovery and stage outputs become available.
- Persist task status and retry history independently. Retry failed stages using saved upstream outputs; permit partial results and aggregate progress at run level.
- All generated tasks remain within their parent run's approved scope and shared resource limits.
- Target-specific modules define discovery strategies, extraction schemas, and classification rules through explicit extension points. Shared machinery handles fetching, execution, storage, limits, and logging.
- Tasks declare required worker capabilities. Workers claim only tasks they support.
- Start with one worker process supporting implemented capabilities; separate HTTP, browser, extraction, or JEV workers later if useful. Capability separation does not require separate services initially.
- Worker count does not multiply approved concurrency, crawl, or model budgets; limits apply across the pool.
- Modules select standard stages; allow fetch-only, extraction from saved pages, and reclassification from saved items when valid inputs exist. Arbitrary workflow graphs are deferred.
- Stage handoffs use references to persisted outputs with producing task, schema, version, and provenance.
- Automatically follow discovered links only within the approved boundaries and remaining budget. Outside-scope discoveries are candidates for separately approved runs.

## Crawlee and modular engine integration

- Select Python and Crawlee for Python as the initial integrated engine, installed as a dependency and wrapped behind a small application-owned adapter interface.
- Supersede mandatory per-URL application jobs: schedule bounded crawl sessions externally, reuse Crawlee's internal URL queue/retries, and persist individual page outcomes. Extraction and JEV remain separate stages/tasks.
- Keep core/public contracts independent of Crawlee types. Permit multiple engine adapters and per-session selection without adopting microservices.
- Modularity means focused component updates without rewriting unrelated application code. Runtime hot-swapping/live migration is not required; ordinary rebuilds and restarts are acceptable. Maintain explicit contracts and persisted-data compatibility.
- Keep source-specific navigation and parsing in adapters, with pure parsing independent of the engine where practical.
- Support manual login and protected profile reuse. Account profiles need exclusive ownership; crawl checkpoints do not substitute for authentication persistence.
- Prioritize Indeed and Naukri source adapters, subject to verified access feasibility. Source support is not implemented yet.
- A browser-based remote console for container login is proposed using noVNC; desktop headful login is an alternative. Exact implementation remains open.

## Scope clarification

Latest storage override: filesystem-backed local records and artifacts now; PostgreSQL later due hardware constraints. The initial slice is single-process and does not implement an application queue or distributed worker guarantees. Keep storage replaceable. Maintain a project changelog and handoff, collect bounded subagent change notes, and commit verified usable slices regularly.

Python, a collection-first milestone, and separate Indeed/Naukri feasibility validation are confirmed. First prove CLI submission, scoped collection, saved evidence, structured extraction, and inspection; add JEV afterward. Controlled fixtures support reliable development independently of live source availability. See [Complete system overview](system-overview.md) for the consolidated diagrams.

Existing job-focused documents describe an initial use case, not the boundary of the core system. Job preferences, detailed schemas, stack choices, and implementation steps are deferred. All project documentation belongs under `/home/abhi/work/jevscout`.
