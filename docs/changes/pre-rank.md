# Structured pre-ranking (before the decision model)

- `modules/jobs/prerank.py`: `pre_rank(job, profile_fields)` → `{score, title, salary, location, reasons}`, all 0–100. Weights: title 45%, location 30%, salary 25%.
- Title: loose token overlap with `role_target` (synonyms such as ml/llm→ai; generic words like "engineer" count 0.4). Location: preferred-location or India match = 100, remote = 60 (100 if `remote_only`), unknown = 50, otherwise 0. Salary: best-effort annual INR from the source-supplied value (static approximate FX) against `min_salary_inr`; undisclosed, zero, or no floor = neutral 50.
- `GET /api/jobs?username=<u>` attaches `pre_rank` to each job. Order and defaults are unchanged without `username`; the frontend sorts by score.
- Checks: `tests/ranking/test_prerank.py`, `tests/api/test_jobs.py`; full backend suite 195 tests, 9 skipped (`cd backend && PYTHONPATH=src ../.venv/bin/python -m unittest discover -s tests -t .`).
- Limits: FX rates are fixed approximations; location matching is substring-based; the pipeline's own `_rank` (skills-weighted) is unchanged; no model is called.
