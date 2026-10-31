# Wellfound source evaluation

Wellfound was evaluated as a possible job discovery source. No adapter was
added: its official Terms restrict harvesting/collection/scraping, and the
documented OAuth MCP integration is for recruiter-authorized applicant data,
not a public jobs feed. The robots file's allowance of some public job URLs does
not itself authorize reuse. There is no permitted, documented job discovery
payload to parse, so no fixture-based parser or tests were added. See
[Wellfound source access research](../wellfound-research.md) for sources and the
proposed contract if Wellfound later authorizes a feed.
