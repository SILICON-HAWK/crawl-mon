# JevScout working agreement

- Work from this repository root. Read `docs/system-architecture.md`, `docs/execution-plan.md`, and `HANDOFF.md` for current scope; the filesystem-first update supersedes earlier database-first diagrams.
- This is a modular Python application. Keep Crawlee and persistence details behind their adapters. Do not write a crawler engine or distributed file queue.
- Use the project TDD skill for meaningful public behavior. Preserve the agreed test boundaries; test one slice at a time with red/green evidence rather than testing internal call structure.
- The coordinator owns integration, shared contracts, changelog/handoff updates, and Git operations. Commit usable verified slices. Do not silently publish or expand the implementation milestone.
- Delegate bounded tasks with allowed files, an agreed contract, checks, and stop conditions. Default to Luna for routine tasks; use stronger models only for a concrete need. Children must not spawn agents or modify unrelated files.
- Every implementing agent writes a short note in its assigned `docs/changes/<task>.md`: behavior, affected files, exact checks/results, limitations, and outstanding work. Do not have parallel agents edit the same changelog.
- The coordinator merges those notes into `CHANGELOG.md` and refreshes the project-root `HANDOFF.md` at stable boundaries. Keep credentials, account cookies, and private data out of all records and commits.
