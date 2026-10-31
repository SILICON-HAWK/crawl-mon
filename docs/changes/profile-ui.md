# Profile editor and job result views

## Behavior

- Added a username-scoped profile editor for freeform context, target role, experience, primary and secondary skills, preferred locations, remote-only preference, and minimum INR salary. It loads and saves through `GET` and `PUT /api/profile/{username}` using `{username, freeform_context, structured_fields}`.
- Pipeline startup uses the current structured editor fields. Freeform context is saved to the profile API but is deliberately omitted from pipeline creation payloads.
- Ranked pipeline jobs and collected run jobs have list/card view controls that adapt to narrow screens. Job records show distinct source listing and apply links when available, plus exposed scoring stats.
- Each job offers an explicit decision-model analysis action. It posts `{username, run_id, job_index}` to `/api/classify`, shows progress, model and returned dimension probabilities, or an error. The profile editor explains that analysis sends saved context and the selected job to OpenRouter after the user chooses Analyze.

## Affected files

- `frontend/src/App.svelte`
- `frontend/src/style.css`

## Checks

- `npm run build` — passed with Vite 6.4.5.

## Limitations and outstanding work

- The UI expects the profile and classification endpoints described above. Backend implementation/integration is owned by the backend task.
- Scoring stats are rendered from known result keys (`scoring_stats`, `scoring_breakdown`, `score_components`, or `decision_stats`); unavailable stats are not synthesized.
