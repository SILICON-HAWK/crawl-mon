# Changelog

Record user-visible behavior, verification, and limitations for each usable slice. Dates are UTC. Agent contribution notes live in `docs/changes/`; the coordinator reviews and incorporates them here before committing. Do not record credentials or private source/profile data.

## Unreleased

### Architecture and execution

- Selected filesystem persistence for the first low-resource implementation. PostgreSQL is the intended later backend, not a required local service.
- Start with a single local process and synchronous operations. Shared application queues, distributed claiming, background execution, and multi-container recovery are deferred; do not approximate them with an untested file queue.
- Keep storage behind a small adapter boundary. Crawlee remains the selected crawling engine; no crawling or classification is implemented in this planning checkpoint.
- Added the phased execution plan and clarified that database-first steps are superseded by the filesystem-first slice.

Verification: documentation whitespace checks. No application checks at this checkpoint.
