# Local vector search research

Added a research note comparing exact job identity, SQLite FTS5, local embeddings with a flat scan, `sqlite-vec`, and PostgreSQL/pgvector for low-hardware semantic job grouping. It recommends an exact and lexical baseline, then an opt-in local embedding experiment only if labeled results show a real gap, with vectors treated as rebuildable derived data.

Files changed: `docs/vector-search-research.md` and this change note.

Checks: reviewed current primary project documentation for SQLite FTS5/compile options, Sentence Transformers, `sqlite-vec`, pgvector, and the local repository architecture. No tests run; documentation-only research. No application behavior or dependency was changed.

Limitations: the semantic quality and runtime cost remain unmeasured on JevScout data and target hardware. Similarity purpose, benchmark corpus, acceptable precision/recall, and latency/RAM budgets need product decisions before implementation.
