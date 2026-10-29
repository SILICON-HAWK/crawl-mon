# JevScout handoff

## Workspace and repository

- Project and Git root: `/home/abhi/work/jevscout`. Run project commands here, not in `/home/abhi/work`.
- Repository: https://github.com/SILICON-HAWK/crawl-mon
- Branch: `main`; SSH remote: `git@github.com:SILICON-HAWK/crawl-mon.git`.
- Last published commit: `27769f9` (consolidated system architecture and diagrams). The existing repository license was preserved.
- This handoff is intentionally in the project folder at the user's request, overriding the handoff skill's temporary-directory default. Check Git history/status for subsequent commits and publication state.

## Current task and stopping point

We are defining architecture through a research and grilling session. No application implementation exists yet. The user wants high-level system boundaries settled first, followed by detailed design and implementation step by step. Do not return to job-profile questions prematurely.

Since the original handoff, Python and Crawlee for Python were selected. The crawler is embedded behind a replaceable adapter; it owns its URL frontier and request retries, while JevScout schedules crawl-session and downstream processing tasks. Modularity means focused code changes, not runtime hot-swapping. Indeed and Naukri are initial target adapters whose access feasibility remains unverified. Manual login/profile reuse is planned; an optional browser console is proposed.

The collection-first milestone is approved: CLI submission, scoped collection, saved evidence, structured extraction, and inspection, then JEV. Target-source feasibility is evaluated separately. The full overview and sequence diagrams are in [System overview](docs/system-overview.md). The current user request is to commit all pending project changes; implementation has not started.

## Read first

1. [System architecture](docs/system-architecture.md): primary architecture, seven Mermaid diagrams, confirmed boundaries, and deferred decisions.
2. [Architecture decisions](docs/architecture-decisions.md): accepted decisions from the grilling session.
3. [JEV research](docs/jev-integration.md): official provider links and verified capabilities; live API access remains untested.
4. [Job-source research](docs/job-source-research.md): official employer-scoped feed APIs and the separate problem of discovering unknown employers.
5. [README](README.md): project overview and document index.

[Earlier architecture/data](docs/architecture.md), [product requirements](docs/product.md), and [roadmap](docs/roadmap.md) contain initial job-focused proposals. The system architecture takes precedence. The job-source research's original first-round questions are historical, not the next agenda.

## Continuing the session

Resume without repeating settled decisions. Python and Crawlee are settled; database and application queue library choices, detailed module contracts, and execution/recovery mechanisms remain open. Define the first implementation slice and meaningful test boundaries before coding. Present remaining recommendations as proposals until accepted.

The user values quality and maintainability without commercial-scale infrastructure. They like flowcharts and explicitly asked for more diagrams. Explain concepts plainly before asking them to choose. Keep research findings distinct from user-approved decisions. Defer detailed job sources, résumé/profile inputs, and scoring preferences until the core architecture is ready.

Agents can operate the future application under explicit user authorization. The intent is bounded execution and approved overrides rather than approval prompts for every read. Refer to the architecture's approval section rather than reinstating the earlier, superseded interpretation that every status check requires approval.

## Suggested skills

- `grilling`: installed at `/home/abhi/.agents/skills/grilling/SKILL.md`. Use for the ongoing architecture interview. Read it before continuing; ask independent decisions in rounds with recommendations and wait for answers.
- `handoff`: installed globally through `npx skills add mattpocock/skills --skill handoff --agent codex --global --yes`, at `/home/abhi/.agents/skills/handoff/SKILL.md`. Use when updating session handoff information; the user's project-folder preference takes precedence over its default location.
- `openai-docs`: use for Codex/app setup and permissions questions, not generic crawler architecture.
- `skill-installer`: use if installing additional skills. The user accepts `npx skills` installation.
- Project-local copies of `find-skills`, `grill-me`, `grilling`, `handoff`, and `tdd` are in `.agents/skills/`. Read the relevant local instructions before use. The TDD skill includes supporting test/mocking guidance; no test suite or application code exists yet.

Use only skills actually available in the new session; inspect their instructions through the provided file-reading tools if no dedicated Skill tool exists. Do not invoke the interview merely because this handoff mentions its trigger phrases; continue it when requested.

## Git and execution environment notes

The environment is WSL Debian. Earlier push failures came from restricted sandbox networking and system SSH files appearing owned by `nobody`; they were not proof of broken GitHub credentials. After permissions allowed escalation, ordinary SSH Git operations outside the sandbox succeeded. Do not change system ownership or DNS based on those earlier symptoms.

Successful fetch/push commands used the execution tool's approved `require_escalated` mode. If a new session encounters the same sandbox-related SSH/network failure, follow its active permission instructions and request escalation where allowed. Do not assume a fresh session has identical permissions.

No credentials belong in this document or project. The current repo contains documentation, `.gitignore`, and its existing license. Documentation links, code fences, and whitespace were checked before the architecture push; application tests do not exist because implementation has not begun.
