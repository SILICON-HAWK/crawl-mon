# Decision scoring engine with provider-agnostic module

## Summary

Implemented vendor-agnostic decision scoring module (`src/jevscout/scoring/`) supporting OpenRouter Decisions API (`respan/span-01-lite:free` by default, with `typesafe/jev-1.13` and other decision models swappable) as well as offline heuristic execution. Connected the scoring engine end-to-end to extracted India jobs with filesystem run persistence and CLI commands (`runs score` and `runs evaluations`).

## Affected files

- `src/jevscout/scoring/__init__.py`: Module exports for decision scoring.
- `src/jevscout/scoring/models.py`: Decision answer primitives (`NoulAnswer`, `ChoiceAnswer`, `ScoreAnswer`), `CandidateProfile`, `JobPosting`, `JobMatchEvaluation`, `RecommendationTier`.
- `src/jevscout/scoring/client.py`: `DecisionClient` protocol, `OpenRouterDecisionClient` (Decisions API wire format, authentication, error mapping), and `LocalHeuristicDecisionClient` (offline scoring).
- `src/jevscout/scoring/rubrics.py`: `build_job_state` serializer and `build_matching_questions` generator (`location_compatibility`, `seniority_fit`, `stack_alignment`).
- `src/jevscout/scoring/engine.py`: `JobMatchEngine` computing weighted composite score (0-100) and recommendation tiers (`STRONG_MATCH`, `REVIEW`, `PASS`).
- `src/jevscout/storage.py`: Added `save_evaluations` and `list_evaluations` to `FileRunStore`.
- `src/jevscout/application.py`: Added `score_run` operation with run lock and atomic persistence.
- `src/jevscout/cli.py`: Added `score` and `evaluations` subcommands under `runs`.
- `tests/test_decision_client.py`: Unit tests for DecisionClient (OpenRouter serialization/errors & local heuristic).
- `tests/test_match_rubrics.py`: Unit tests for question building and state serialization.
- `tests/test_scoring_engine.py`: Unit tests for composite score calculation and recommendation tiers.
- `tests/test_result_storage.py`: Unit tests for evaluations persistence.
- `tests/test_application.py`: Integration test for `score_run`.
- `tests/test_cli.py`: CLI test for `runs score --offline` and `runs evaluations`.
- `tests/test_feed_integration.py`: End-to-end test from feed scraping to India extraction to decision evaluation.

## Checks and evidence

- Total 104 tests passing across full suite:
  `python -m unittest discover -s tests` -> 104 tests in 27.8s, OK.
- Unit tests for scoring:
  `python -m unittest tests/test_decision_client.py tests/test_match_rubrics.py tests/test_scoring_engine.py` -> 10 tests, OK.
- CLI smoke test:
  `python -m unittest tests/test_cli.py` -> 5 tests, OK.
- Storage and application verification:
  `python -m unittest tests/test_result_storage.py tests/test_application.py` -> 7 tests, OK.

## Limitations and outstanding work

- Live OpenRouter calls require setting `OPENROUTER_API_KEY` in environment.
- The default model is `respan/span-01-lite:free`; for paid high-tier matching, `--model typesafe/jev-1.13` can be passed.
- Candidate profiles currently load from CLI parameters or `--profile-json <path>`. Next steps can include candidate profile persistence and common employer seed catalogs.
