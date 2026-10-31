# Frontend MVP

## Behavior

- Added a local Svelte/Vite dashboard for run and pipeline status, plus run result inspection.
- Added a visible pipeline start form that requires user supplied seed URLs and a candidate profile JSON object before sending `POST /api/pipeline`. The editable profile example uses the API schema (`role_target`, skills, years, preferred locations, remote preference, and optional salary floor).
- Added ranked pipeline result inspection with score, recommendation, matched skills, source provenance, and a job link when present.
- Dashboard calls `GET /api/runs`, `GET /api/runs/{id}/results`, `GET /api/pipeline`, and `GET /api/pipeline/{id}`. Vite proxies API calls to the loopback backend at port 8000 by default.
- Both Vite dev and preview servers bind to `127.0.0.1` by default.

## Files

- `frontend/package.json`, `frontend/package-lock.json`, `frontend/index.html`, `frontend/vite.config.js`
- `frontend/src/App.svelte`, `frontend/src/main.js`, `frontend/src/style.css`
- `frontend/README.md`

## Checks

- `npm run build` — passed (Vite 6.4.5 production build).

## Limitations and outstanding work

- API integration is browser-level and was not exercised against a running backend in this slice.
- Candidate profile fields remain editable JSON so additional profile fields do not require a UI release; no seed URLs are hidden in the page.
- The frontend build reports 3 low severity dependency audit findings from npm; no audit remediation was attempted in this UI slice.
