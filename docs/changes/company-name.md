# Employer name extraction

Updated Ashby, Greenhouse, Lever, Recruitee, Breezy, and Teamtailor feed parsers to populate `company` only from explicit employer fields on a posting. Department and team fields no longer become company names. When a feed posting does not name its employer, `company` is `null`.

The current sample payloads for all six providers contain department/team data but no employer field. Their board identifiers and URL hostnames identify the feed account or board, but are not emitted as employer names because those values are not explicit posting data. Feed integrations that possess an authoritative company name at the board/source level can provide it in a follow-up source mapping.

Parser tests cover both the missing-employer case and explicitly supplied company fields for each provider.

Coordinator integration adds a small explicit board-to-employer mapping for SonicWall, Firstwork, and TransPerfect. Existing saved runs were re-extracted only after confirming job identities and ordering stayed the same, so stored decision references remain valid.
