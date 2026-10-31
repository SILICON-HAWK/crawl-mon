# Local job search and semantic grouping research

Research date: 2026-10-31. This is a design recommendation for a later JevScout increment. It does not select a dependency or authorize implementation.

## Recommendation

Start with deterministic exact-duplicate handling plus lexical search using SQLite FTS5, if/when full-text search is requested. Add local semantic similarity only after a small labeled job set shows that lexical matching misses useful near-duplicates or related-role groups. For that experiment, keep embeddings optional and local, compute them on demand or in a bounded batch, persist model/version metadata, and initially use a simple exact cosine scan over a compact index. Keep the index rebuildable from saved extracted job records. Do not add a vector extension or make PostgreSQL a prerequisite for the first semantic experiment.

This is a staged recommendation, not a claim that embeddings will improve JevScout's results. The product should first define whether a “group” means same opening across feeds, reposts of one opening, or related roles. Similarity is a ranking signal; it must not automatically merge records or suppress applications.

## Existing constraints and input data

JevScout's current first-class persistence is filesystem based; PostgreSQL is an optional adapter and future multi-writer backend. The base Python package has no runtime dependencies. Extracted results already have provenance and fields such as title, company, location, description summary, and application URL. These provide enough inputs for an offline experiment without re-fetching sources. Exact URL canonicalization is already used in the API's cross-run aggregation; prefer that and source job identifiers for high-confidence duplicate identity.

An embedding index should therefore be a derived cache, never the authority for job records or provenance. A missing, stale, corrupt, or unsupported index must not make saved jobs unavailable. Recompute from extracted records and record the embedding model identifier, revision, text construction/version, dimensions, and timestamp. Keep any profile/resume input out of the initial grouping experiment; job-to-job comparison does not need it.

## Options and tradeoffs

| Option | Quality and behavior | Resource and operational cost | Fit for this project |
| --- | --- | --- | --- |
| Exact keys and normalized fields | Strong for identical source IDs or canonical application URLs; deterministic. Title/company/location rules can catch some variants but miss paraphrases and risk false merges. | Negligible compute; simple filesystem metadata or SQL. | Keep as the first dedupe layer. Never use fuzzy similarity as a destructive identity key. |
| SQLite FTS5 lexical retrieval | Finds matching terms, phrases, prefixes, and proximity; BM25 ranking is built in. Good for exact skills, employers, locations, technologies, and explainable keyword queries. Does not understand synonyms or paraphrase (“SRE” vs “site reliability engineer”) without query expansion. | Small local index; no model download, GPU, remote service, or vector dependency. SQLite builds may omit FTS5, so check capability at initialization and provide a clear unsupported/fallback path. | Best first search layer when lexical search is needed. SQLite's official docs describe FTS5 as a full-text index and document BM25, tokenizers, and optional compile-time availability. |
| Local embeddings plus flat exact scan | Can surface paraphrases and semantically related descriptions, but may rank related roles above true reposts. Similarity scores are not calibrated probabilities and thresholds need human-labeled validation. | One local model inference dependency and model files/cache; CPU latency and RAM vary by runtime and machine. A flat scan uses O(N·d) comparisons, which is easy to reason about and avoids index tuning at small/medium collections; profile before scaling. | Preferred proof of value: keep vector math/index simple and rebuildable. Existing optional dependencies are zero by default, so this must remain an explicit opt-in extra/feature. |
| SQLite vector extension (`sqlite-vec`) | Adds SQL KNN and metadata filtering in an embedded database; helps keep vectors and records together. Does not improve embedding quality or determine a safe grouping threshold. | Native extension/binary and distribution/loading compatibility add support burden. Project describes itself as pre-v1 and warns of breaking changes; test availability and persistence behavior on supported platforms before adopting. | Reconsider after flat-scan profiling demonstrates a bottleneck and the extension's maturity/platform support meet project needs. Not a first dependency. |
| PostgreSQL with pgvector | Central SQL storage and vector operators/indexes, useful when several processes/users need shared records and concurrent writes. HNSW/IVFFlat trade query speed, memory/build cost, and recall; approximate indexing adds tuning. | Requires the already-optional PostgreSQL deployment and extension lifecycle. Adds operational cost that is not justified by low-hardware single-user local grouping. | Future multi-user/multi-writer stage only if PostgreSQL is selected for broader persistence needs. Keep it as an adapter option, not a reason to require a server now. |

Primary documentation: [SQLite FTS5](https://www.sqlite.org/fts5.html), [SQLite compile options](https://www.sqlite.org/compile.html), [`sqlite-vec` project README](https://github.com/asg017/sqlite-vec), [pgvector README](https://github.com/pgvector/pgvector), and [Sentence Transformers semantic search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html).

## Model and privacy notes

Sentence Transformers documents an embedding workflow for semantic search and similarity. Its `all-MiniLM-L6-v2` model card lists 22.7M parameters and 384-dimensional embeddings; that makes it a plausible CPU-oriented candidate for an experiment, not a hardware guarantee or endorsed production choice. Benchmark cold model load, warm per-job inference, peak resident memory, and index size on the actual target machine before selecting it. Downloading a model is a network action at setup time; inference can then run locally, but the model files and cache need storage and update policy. A pure local pipeline can avoid transmitting job text and profile data to a hosted embedding API; keep model telemetry/network behavior verified and make the selected model visible to the user.

Embedding similarity is sensitive to which text is encoded. Start with title, company, location, and a bounded/normalized description excerpt rather than blindly embedding raw HTML or unlimited page text. Preserve fields separately so the system can combine semantic score with exact URL/company/location evidence and expose why two jobs were suggested together. Do not assume a universal score threshold; evaluate precision/recall on a hand-labeled set, including reposts, distinct openings at one company, staffing-agency copies, title variants, and generic descriptions.

References: [all-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), [Sentence Transformers semantic search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html).

## Proposed incremental plan

1. Define two separate outcomes: exact duplicate detection (URL/source ID first) and optional “similar jobs” suggestions (non-destructive). Agree how users inspect and dismiss suggestions.
2. Collect a small representative saved-result set and label duplicate, repost, related, and unrelated pairs. Include missing descriptions and cross-source copies.
3. Establish a lexical/exact baseline with normalized URL/company/title/location fields. If lexical job search is in scope, use FTS5 behind a capability check; preserve a usable fallback where SQLite lacks FTS5.
4. Add a disposable experiment script or isolated optional module using a pinned, locally runnable sentence embedding model. Benchmark CPU/RAM/cold start and compare top-k ranking against the labeled set. Keep the model out of base dependencies and the default run path.
5. If evaluation shows a material improvement, define thresholds and human review behavior; persist vectors as rebuildable derived data keyed by record identity and model/text version. Keep exact duplicate IDs and provenance independent of similarity output.
6. Start with exact cosine scan. Consider `sqlite-vec` only if measured query latency at actual collection sizes is inadequate and platform/install checks pass. Consider pgvector only after shared PostgreSQL is needed for concurrent or multi-user persistence, and then measure index recall and resource costs.

## Trigger criteria

Move beyond exact keys and lexical search only when representative labeled examples show a recurring, user-visible miss that semantic similarity can address, and a local CPU benchmark meets the project's target-machine latency and memory limits. Add an ANN/vector extension only when a measured flat-scan bottleneck remains after sensible filtering. Move storage to PostgreSQL/pgvector only when the product requires shared concurrent access or corpus scale beyond local single-user operation, not merely to enable vectors.

## Scope and non-goals

This research covers local job-to-job retrieval, grouping, and deduplication options for low-hardware use. It does not implement a search UI, embeddings, model downloads, index migrations, a similarity threshold, automatic record merging, resume-to-job matching, a hosted embedding integration, a PostgreSQL migration, or a benchmark claim. It does not establish a specific RAM/latency budget; that must be measured on supported hardware.
